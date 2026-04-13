document
  .getElementById("signin-form")
  .addEventListener("submit", async function (e) {
    e.preventDefault();
    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    // Convert to JSON for Node backend (Flask version used request.form, but this is cleaner)
    try {
      const res = await fetch("/api/signin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await res.json();

      if (result.success) {
        window.location.href = "/";
      } else {
        document.getElementById("alert-box").innerHTML = `
                <div class="alert alert-danger">${result.message}</div>
            `;
      }
    } catch (err) {
      console.error(err);
    }
  });
