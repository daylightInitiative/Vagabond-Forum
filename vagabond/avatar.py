from PIL import Image
from random import randint, choice
from pathlib import Path
from hashlib import md5
from vagabond.utility import DBManager

# creates random pixel based avatar similar to github and stackoverflow

APP_FOLDER = Path(__file__).parent
STATIC_FOLDER = APP_FOLDER / "static"
AVATARS_FOLDER = STATIC_FOLDER / "avatars"

def update_user_avatar(db: DBManager, userID: int, avatar_hash: str) -> None:
    update_avatar = db.write(query_str="""
        UPDATE users
        SET avatar_hash = %s
        WHERE id = %s
    """, params=(avatar_hash, userID,))    
    return None

random_colors = [
    (255,86,213), # pink
    (255,174,47), # orange
    (112,255,165), # lime
    (75,80,255), # blue
    (123,0,205), # purple
    (15,15,15) # black
]

color_white = (255, 255, 255)
max_size = (420, 420) # the size github uses
size = (420, 210) #the left side
block_size = (50, 50)
# 420/2 = flat 210.0

def create_block(img, mapDict, row, col, color):

    for x in range(block_size[0]):
        for y in range(block_size[1]):
            xpos = col * block_size[0]
            ypos = row * block_size[1]
            img.putpixel((xpos + x, ypos + y), color)
    mapDict.update({
        (row, col): 1
    })

def get_available_row_col(mapDict) -> tuple[int, int]:
    grid_cols = size[0] // block_size[0]
    grid_rows = size[1] // block_size[1]
    row, col = randint(0, grid_cols - 1), randint(0, grid_rows - 1)
    while mapDict.get((row, col)):
        row, col = randint(0, grid_cols - 1), randint(0, grid_rows - 1)
    return row, col

def merge(im1: Image.Image, im2: Image.Image) -> Image.Image:
    w = (im1.size[0] - 210) + (im2.size[0] + 210)
    h = max(im1.size[1], im2.size[1])
    im = Image.new("RGB", (w, h))

    im.paste(im1)
    im.paste(im2, (im1.size[0], 0))

    return im

def create_user_avatar(userid: int) -> str:
    columns_taken = {}
    avatar_color = choice(random_colors)
    avatar_base = Image.new(mode='RGB', size=max_size, color=color_white)

    for i in range(1, 16):
        row, col = get_available_row_col(mapDict=columns_taken)
        create_block(img=avatar_base, mapDict=columns_taken, row=row, col=col, color=avatar_color)

    second_base = avatar_base.transpose(Image.FLIP_LEFT_RIGHT)
    third_base = merge(second_base, avatar_base)
    width, height = third_base.size
    left = (width - 420) // 2
    right = left + 420
    cropped = third_base.crop((left, 0, right, 420))

    # based on the userid lets generate a unique md5 hash
    hash_object = md5()
    hash_object.update(f"{userid}".encode('utf-8'))
    hash_str = hash_object.hexdigest()

    FILE_PATH = AVATARS_FOLDER / (hash_str + ".jpg")
    cropped.save(FILE_PATH)

    return hash_str