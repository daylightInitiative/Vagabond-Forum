let text_box = document.getElementById("description");
let old_content = "";

// we want this to get only on page load
async function get_saved_draft() {
    try {

        const response = await fetch("/save_draft");
        if(!response.ok) {
            throw new Error(`Reponse status: ${response.status}`);
        }
        const data = await response.json();

        // get the "contents" from the returned json
        console.log("received data from the server!");
        if(data != null) {
            //console.log(data);
            text_box.value = data.contents;
        }

    } catch (error) {
        console.log(error);
    }
}

async function save_draft() {
    try {
        
        let current_contents = text_box.value;
        // we dont want it to be saving empty strings
        if((old_content === current_contents) || current_contents === "") {
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

// only call this once
get_saved_draft();
const save_draft_interval_id = setInterval(save_draft, 8000);
text_box.addEventListener("change", function() {
    console.log("changed");
    save_draft();
})


