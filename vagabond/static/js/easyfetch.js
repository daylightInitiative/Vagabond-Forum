

// a simple wrapper around the fetch function that returns the json from the request
// automatically passes the csrf token and appropriate headers for json
export async function easyfetch(url, data = {}) {
    try {
        data.headers = data.headers || {};

        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        if (!csrfToken) {
            console.error("easyfetch: missing <meta name='csrf-token'> tag");
            return null;
        }
        data.headers["X-CSRFToken"] = csrfToken;

        const method = (data.method || 'GET').toUpperCase();
        // hacky way of adjusting for json
        if (data.body && typeof data.body === "object" && method !== 'GET' && method !== 'HEAD') {
            data.headers["Content-Type"] = "application/json; charset=UTF-8";
            data.body = JSON.stringify(data.body);
        }
        const response = await fetch(url, data);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`easyfetch: request failed (${response.status}), ${errorText}`);
        }

        // it returns if any, json
        return response.json ? await response.json() : response;
    } catch (error) {
        console.log(`easyfetch failed with error: ${error}`);
        throw error;
    }
}
