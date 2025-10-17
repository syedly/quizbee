// Switch input type
function showInput(type) {
  document.querySelectorAll(".input-box").forEach(box => box.classList.add("hidden"));
  document.querySelector("#input-" + type).classList.remove("hidden");

  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelector("#btn-" + type).classList.add("active");
}

// Sidebar toggle for mobile
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");
const menuBtn = document.getElementById("menuBtn");

menuBtn.addEventListener("click", () => {
  sidebar.classList.toggle("sidebar-closed");
  overlay.classList.toggle("hidden");
});

overlay.addEventListener("click", () => {
  sidebar.classList.add("sidebar-closed");
  overlay.classList.add("hidden");
});

  tailwind.config = {
    darkMode: "class",
    theme: {
      extend: {
        colors: {
          primary: "#3713ec",
          "background-light": "#f6f6f8",
          "background-dark": "#131022",
        },
        fontFamily: {
          display: ["Space Grotesk"],
        },
      },
    },
  };

// ====== Theme Switch Handling ======
document.addEventListener("DOMContentLoaded", () => {
  const modeToggle = document.querySelector('input[name="light_mode"]');
  if (modeToggle) {
    modeToggle.addEventListener("change", () => {
      if (modeToggle.checked) {
        // Light mode
        document.documentElement.classList.remove("dark");
        document.body.classList.add("bg-background-light", "text-gray-800");
        document.body.classList.remove("bg-background-dark", "text-gray-200");
      } else {
        // Dark mode
        document.documentElement.classList.add("dark");
        document.body.classList.add("bg-background-dark", "text-gray-200");
        document.body.classList.remove("bg-background-light", "text-gray-800");
      }
    });
  }
});
