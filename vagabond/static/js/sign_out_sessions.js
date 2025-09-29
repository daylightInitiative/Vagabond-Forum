const signout = document.getElementById("sign-out-sessions");
const status = document.getElementById("status-text");

function delay(time) {
    return new Promise(resolve => setTimeout(resolve, time));
}

async function display_status_msg(element, text) {
    element.style.display = 'block';
    element.innerHTML = text;
    await delay(3000);
    element.style.display = 'none';
    element.innerHTML = "";
}

async function sign_out_of_all_other_sessions() {
    try {

        const response = await fetch('/invalidate_other_sessions', {
            method: "POST",
            body: JSON.stringify({
            }),
            headers: {
                "Content-type": "application/json; charset=UTF-8"
            }
        })

        if (!response.ok) {
            display_status_msg(status, "Error: There was an error signing out other sessions");
            throw new Error(`Reponse status: ${response.status}`);
        }

        // create our new interval
        display_status_msg(status, "Successfully signed out other sessions");
    } catch (error) {
        console.log(error);
    }
}

// its more reliable to hook this after the dom is loaded
document.addEventListener("DOMContentLoaded", (event) => {
    signout.onclick = function() {
        console.log("signing out of all other sessions...");
        sign_out_of_all_other_sessions();
    };
});

