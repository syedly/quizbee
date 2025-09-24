(function () {
  const subjectControls = document.getElementById("qzSubjectControls");
  const originalHTML = subjectControls.innerHTML;

  // ---------------------------
  // Subject Control Switcher
  // ---------------------------
  subjectControls.addEventListener("change", function (e) {
    if (e.target.id !== "qz-subject-select") return;

    const v = e.target.value;
    subjectControls.innerHTML = originalHTML; // reset base select

    let extraControls = "";

    if (v === "prompt") {
      extraControls = `
        <input class="qz-prompt" id="qzPromptInput" placeholder="Enter prompt">
      `;
    } else if (v === "url") {
      extraControls = `
        <input class="qz-prompt" id="qzUrlInput" placeholder="Enter a URL">
      `;
    } else if (v === "import") {
      extraControls = `
        <button id="qzImportBtn">Import Data</button>
      `;
    } else if (v === "upload") {
      extraControls = `
        <input type="file" id="qzFileInput">
      `;
    } else if (v === "text") {
      extraControls = `
        <textarea id="qzTextArea" placeholder="Enter your text here"></textarea>
      `;
    }

    // Always append topic + subtopic selects
    subjectControls.innerHTML += `
      ${extraControls}
      <select id="qz-topic-select"><option value="">Choose a Topic</option></select>
      <select id="qz-subtopic-select"><option value="">Choose a Sub-Topic</option></select>
    `;
  });

  // ---------------------------
  // Build Quiz Button Handler
  // ---------------------------
  document.addEventListener("DOMContentLoaded", () => {
    const buildBtn = document.getElementById("qzBuildBtn");
    if (!buildBtn) return;

    buildBtn.addEventListener("click", async () => {
      // Core inputs
      const subject = document.getElementById("qz-subject-select")?.value || "";
      const topic = document.getElementById("qz-topic-select")?.value || subject;
      const subtopic = document.getElementById("qz-subtopic-select")?.value || "";

      const type = document.getElementById("qz-type")?.value || "mix";
      const count = document.getElementById("qz-count")?.value || 5;
      const lang = document.getElementById("qz-lang")?.value || "English";
      const diff = document.getElementById("qz-diff")?.value || 1;

      // Extra inputs
      const promptText = document.getElementById("qzPromptInput")?.value || "";
      const urlText = document.getElementById("qzUrlInput")?.value || "";
      const customText = document.getElementById("qzTextArea")?.value || "";
      const fileInput = document.getElementById("qzFileInput")?.files?.[0] || null;

      // Build FormData
      const formData = new FormData();
      formData.append("topic", topic || "General");
      formData.append("language", lang);
      formData.append("num_questions", count);
      formData.append("difficulty", diff);
      formData.append("question_preference", type);

      if (promptText) formData.append("prompt", promptText);
      if (urlText) formData.append("url", urlText);
      if (customText) formData.append("text", customText);
      if (fileInput) formData.append("file", fileInput);

      try {
        const response = await fetch("/generate_quiz/", {
          method: "POST",
          headers: { "X-CSRFToken": getCSRFToken() },
          body: formData,
        });

        if (!response.ok) {
          alert("Error building quiz!");
          return;
        }

        // Render returned HTML
        const html = await response.text();
        document.body.innerHTML = html;
      } catch (err) {
        console.error("Error:", err);
        alert("Something went wrong!");
      }
    });

    // Helper for CSRF
    function getCSRFToken() {
      const name = "csrftoken";
      const cookies = document.cookie.split(";");
      for (let cookie of cookies) {
        const c = cookie.trim();
        if (c.startsWith(name + "=")) {
          return c.substring(name.length + 1);
        }
      }
      return "";
    }
  });
})();
