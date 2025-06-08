document.addEventListener('DOMContentLoaded', function() {
    // Add a Refresh Button
    const container = document.querySelector('.container');
    const refreshBtn = document.createElement('button');
    refreshBtn.className = 'btn btn-secondary mb-4';
    refreshBtn.innerText = 'Refresh News';
    refreshBtn.onclick = function() {
        fetch('/fetch-articles')
            .then(response => response.text())
            .then(() => location.reload());
    };
    container.insertBefore(refreshBtn, container.firstChild);

    // Auto-refresh every 5 minutes
    setInterval(() => {
        fetch('/fetch-articles')
            .then(response => response.text())
            .then(() => location.reload());
    }, 300000); // 5 minutes
});
