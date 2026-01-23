

// a simple wrapper around the fetch function that returns the json from the request
// automatically passes the csrf token and appropriate headers for json
// updated to also support clean URL query parameters
export async function easyfetch(url, options = {}, queryParams = null) {
    try {
        // unpacking (copy) additional headers so we dont change the original values
        const headers = { ...(options.headers || {}) };

        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfMeta?.getAttribute('content');

        if (!csrfToken) {
            console.error("easyfetch: missing <meta name='csrf-token'>");
            return { ok: false, error: "Missing CSRF token" };
        }

        headers["X-CSRFToken"] = csrfToken;

        const method = (options.method || "GET").toUpperCase();
        let body = options.body;

        if (body && typeof body === "object" && method !== "GET" && method !== "HEAD") {
            headers["Content-Type"] = "application/json; charset=UTF-8";
            body = JSON.stringify(body);
        }

        let finalURL = url;
        if (queryParams && Object.keys(queryParams).length > 0) {
            const queryURL = new URL(url, window.location.origin);

            // originally was going to do this the easy way, but its better to use the API to handle multiple during dev
            for (const [k, v] of Object.entries(queryParams)) {
                queryURL.searchParams.set(k, v);
            }
            finalURL = queryURL.toString();
        }

        const response = await fetch(finalURL, {
            ...options,
            method,
            headers,
            body
        });

        if (!response.ok) {
            const errorText = await response.text().catch(() => null);
            return {
                ok: false,
                status: response.status,
                error: errorText || response.statusText
            };
        }

        let data = null;
        const contentType = response.headers.get("content-type");
        if (contentType?.includes("application/json")) {
            data = await response.json();
        }

        return { ok: true, data };
    } catch (error) {
        console.error("easyfetch failed with error:", error);
        return { ok: false, error };
    }
}