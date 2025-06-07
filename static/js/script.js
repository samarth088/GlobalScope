document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.container');
    const refreshBtn = document.createElement('button');
    refreshBtn.className = 'btn btn-secondary mb-4';
    refreshBtn.innerText = 'Refresh News';
    refreshBtn.onclick = function() {
        location.reload();
    };
    container.insertBefore(refreshBtn, container.firstChild);
});
