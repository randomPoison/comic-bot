// Register a click handler for all like buttons in the page. All the handler
// does is post to `/likes/<id>` and then update the button's contents with the
// number of likes in the response.
document.addEventListener('DOMContentLoaded', () => {
    const likeButtons = document.querySelectorAll('.like-button');

    likeButtons.forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            const btn = event.currentTarget;
            const id = btn.getAttribute('data-id');

            // Disable the button to prevent multiple clicks.
            btn.disabled = true;

            fetch(`/like/${id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                btn.textContent = `🌟 ${data.likes}`;
                btn.disabled = false;
            })
            .catch(error => {
                console.error('Error:', error);
                btn.disabled = false;
                alert('Failed to like. Please try again.');
            });
        });
    });
});
