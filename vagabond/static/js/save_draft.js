let text_box = document.getElementById("description");
let old_content = "";

async function save_draft() {
    try {
        
        let current_contents = text_box.value;
        if(old_content === current_contents) {
            return; // um dont send a request when nothing has changed
        }

        const response = await fetch('/save_draft', {
            method: "POST",
            body: JSON.stringify({
                contents: current_contents
            }),
            headers: {
                "Content-type": "application/json; charset=UTF-8"
            }
        })

        if (!response.ok) {
            throw new Error(`Reponse status: ${response.status}`);
        }

        console.log("saved draft to server...");
        old_content = current_contents;
    } catch (error) {
        console.log(error);
    }
}

const save_draft_interval_id = setInterval(save_draft, 8000);
text_box.addEventListener("change", function() {
    console.log("changed");
    save_draft();
})


