from PIL import Image
from random import randint, choice, seed
from pathlib import Path
from hashlib import sha256
from vagabond.services import dbmanager

# creates random pixel based avatar similar to github and stackoverflow

APP_FOLDER = Path(__file__).parent
STATIC_FOLDER = APP_FOLDER / "static"
AVATARS_FOLDER = STATIC_FOLDER / "avatars"

# update the users.avatar_hash with a hash that is the name of their individual avatar found in /static/avatars/
def update_user_avatar(userID: int, avatar_hash: str) -> None:
    dbmanager.write(query_str="""
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

def get_available_row_col(mapDict, userID: int) -> tuple[int, int]:
    grid_cols = size[0] // block_size[0]
    grid_rows = size[1] // block_size[1]

    seed(userID)
    row, col = randint(0, grid_cols - 1), randint(0, grid_rows - 1)
    while mapDict.get((row, col)):
        row, col = randint(0, grid_cols - 1), randint(0, grid_rows - 1)
    return row, col

# simplified merge, synopsis: copies an image and pastes it to the right by (img1.size[0]) pixels
def merge(im1: Image.Image, im2: Image.Image) -> Image.Image:
    w = im1.size[0] + im1.size[0]
    h = max(im1.size[1], im2.size[1])

    im = Image.new("RGB", (w, h))

    im.paste(im1)
    im.paste(im2, (im1.size[0], 0))

    return im

def create_user_avatar(userid: int) -> str:
    columns_taken = {}
    seed(userid) # to avoid constant readdition of fluff files lets seed it
    avatar_color = choice(random_colors)
    avatar_base = Image.new(mode='RGB', size=max_size, color=color_white)

    for i in range(1, 16):
        row, col = get_available_row_col(mapDict=columns_taken, userID=userid)
        create_block(img=avatar_base, mapDict=columns_taken, row=row, col=col, color=avatar_color)

    second_base = avatar_base.transpose(Image.FLIP_LEFT_RIGHT)
    third_base = merge(second_base, avatar_base)

    #(removing the hardcoded sizes if we want to upscale later)
    crop_width = avatar_base.size[0]
    width, height = third_base.size
    left = (width - crop_width) // 2
    right = left + crop_width
    cropped = third_base.crop((left, 0, right, crop_width)) # crop from 210 -> 630(210+420) = 210 1 1/2 of the image

    # based on the userid lets generate a unique md5 hash
    hash_object = sha256() # no upside to using a weaker md5 hash (less collisions)
    hash_object.update(f"{userid}_profile".encode('utf-8'))
    hash_str = hash_object.hexdigest()

    # get the first two bytes
    hashbyte1 = hash_str[:2]
    hashbyte2 = hash_str[2:4]

    # seperate each file by its first two bytes so its more organized
    DIVIDER_FOLDER = AVATARS_FOLDER / hashbyte1 / hashbyte2
    DIVIDER_FOLDER.mkdir(parents=True, exist_ok=True)

    FILE_NAME = hash_str + ".jpg"
    FILE_PATH = DIVIDER_FOLDER / FILE_NAME
    cropped.save(FILE_PATH)

    relative_path = f'/static/avatars/{hashbyte1}/{hashbyte2}/{FILE_NAME}'

    return relative_path