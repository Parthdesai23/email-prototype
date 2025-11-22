async function generateEmail() {
    const prompt = document.getElementById("prompt").value;
    const backendUrl = "https://your-render-backend-url.com/generate-email";

    const response = await fetch(backendUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
    });

    const data = await response.json();
    const html = data.html;

    document.getElementById("preview").srcdoc = html;
}
