let current = 1;
let total = 0; // will be set from template
let timer;
let timeLeft = 60;

function initQuiz(totalQuestions) {
    total = totalQuestions;
    showQuestion(1);
}

function showQuestion(num) {
    // Hide all questions
    document.querySelectorAll(".question-container").forEach(div => div.style.display = "none");

    // Show the current question
    let q = document.getElementById("question-" + num);
    if (q) q.style.display = "block";

    // Reset and start timer
    timeLeft = 60;
    updateTimer(num);
    clearInterval(timer);
    timer = setInterval(() => {
        timeLeft--;
        updateTimer(num);
        if (timeLeft <= 0) {
            clearInterval(timer);
            nextQuestion(num);
        }
    }, 1000);
}

function updateTimer(num) {
    let el = document.getElementById("timer-" + num);
    if (el) el.textContent = "Time left: " + timeLeft + "s";
}

function nextQuestion(num) {
    if (num < total) {
        showQuestion(num + 1);
    } else {
        document.querySelectorAll(".question-container").forEach(div => div.style.display = "none");
        document.getElementById("submitSection").style.display = "block";
    }
}
