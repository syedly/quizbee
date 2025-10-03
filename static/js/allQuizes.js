  // SweetAlert popup -> submits Django form
  function openShareForm(quizId) {
    Swal.fire({
      title: 'Share Quiz',
      input: 'text',
      inputPlaceholder: 'Enter username',
      showCancelButton: true,
      confirmButtonText: 'Share',
      preConfirm: (username) => {
        if (!username) {
          Swal.showValidationMessage('Please enter a username');
          return false;
        }
        // put username into hidden input + submit form
        document.getElementById("username-" + quizId).value = username;
        document.getElementById("share-form-" + quizId).submit();
      }
    });
  }
// static/js/allQuizes.js

// Rotate the meter needle based on difficulty (1–5 scale)
function rotateNeedle(quizId, difficulty) {
    const needle = document.getElementById("needle-" + quizId);
    if (!needle) return;

    // difficulty ranges 1–5, map to -90° (left) → +90° (right)
    const minAngle = -90;
    const maxAngle = 90;
    const step = (maxAngle - minAngle) / 4;  // 4 intervals (between 5 levels)

    // Calculate angle
    const angle = minAngle + (difficulty - 1) * step;

    // Apply rotation
    needle.style.transform = `translateX(-50%) rotate(${angle}deg)`;
}
