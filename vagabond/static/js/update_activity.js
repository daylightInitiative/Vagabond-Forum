
async function send_exit_page_analytics() {
    try {

        const url = window.location.pathname;
        // in an ideal world, we would want to contact an analytics subdomain or microservice, but we're poor so...
        // and adding this would be the equilvilant of google analytics
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        const response = await fetch('/analytics', {
            method: "POST",
            headers: {
                "Content-type": "application/json; charset=UTF-8",
                "X-CSRFToken": csrfToken
            },
            body: JSON.stringify({
                "exitpage": url
            })
        })

        if (!response.ok) {
            console.log(status, "Error: There was an error sending analytics");
            throw new Error(`Reponse status: ${response.status}`);
        }

    } catch (error) {
        console.log(error);
    }
}



document.addEventListener("DOMContentLoaded", (event) => {
    window.addEventListener("beforeunload", send_exit_page_analytics);
});