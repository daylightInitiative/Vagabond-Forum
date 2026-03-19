import { easyfetch } from '/static/js/easyfetch.js';

async function send_exit_page_analytics() {
    try {

        const url = window.location.pathname;
        // in an ideal world, we would want to contact an analytics subdomain or microservice, but we're poor so...
        const response = await easyfetch('/analytics', {
            method: "POST",
            body: {
                exitpage: url
            }
        });

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