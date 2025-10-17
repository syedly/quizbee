// quiz_actions.js

// Open the Share Modal
function openShareModal(quizId) {
    document.getElementById("quizId").value = quizId;
    document.getElementById("shareForm").action = `/quiz/${quizId}/share/`;  // set the form action dynamically
    document.getElementById("shareModal").classList.remove("hidden");
}

// Close the Share Modal
function closeShareModal() {
    document.getElementById("shareModal").classList.add("hidden");
}

// Optional: you can add other JS functions like your sidebar toggle here if needed
