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