// JavaScript code to fetch and display videos
        document.addEventListener('DOMContentLoaded', () => {
            const videoContainer = document.getElementById('videoContainer');

            // Your API endpoint
            const apiUrl = '/api/most-viewed-videos/UCaB3YPxB_eXqTcFdFo9CrCA/?max_results=3';

            // Fetch video data from the API
            fetch(apiUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.videos && data.videos.length > 0) {
                        // Generate HTML for each video
                        const videoHtml = data.videos.map(video => createVideoCard(video)).join('');
                        // Insert the generated HTML into the container
                        videoContainer.innerHTML = videoHtml;
                    } else {
                        videoContainer.innerHTML = '<p>No videos found.</p>';
                    }
                })
                .catch(error => {
                    console.error('Error fetching videos:', error);
                    videoContainer.innerHTML = '<p>Oops! Something went wrong while loading videos.</p>';
                });
        });

        // Function to create a video card HTML
        function createVideoCard(video) {
            const videoDate = new Date(video.publishedAt);
            const formattedDate = videoDate.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });

            return `
                <div class="col-lg-4 col-md-6">
                    <article class="video-card">
                        <div class="video-wrapper">
                            <iframe 
                                src="https://www.youtube.com/embed/${video.videoId}"
                                title="${video.title}"
                                frameborder="0"
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowfullscreen
                            ></iframe>
                        </div>
                        <div class="video-content">
                            <span class="video-category">Most Viewed</span>
                            <h3 class="video-title">${sanitizeHTML(video.title)}</h3>
                            <div class="video-meta">
                                ${formattedDate} • ${formatViewCount(video.viewCount)} views
                            </div>
                            <p class="video-description">
                                ${sanitizeHTML(video.description.slice(0, 100))}...
                            </p>
                            <a href="https://www.youtube.com/watch?v=${video.videoId}" 
                               class="watch-more" 
                               target="_blank" 
                               rel="noopener noreferrer">
                                Watch on YouTube
                            </a>
                        </div>
                    </article>
                </div>
            `;
        }

        // Function to sanitize HTML (prevent XSS)
        function sanitizeHTML(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        // Function to format view count
        function formatViewCount(views) {
            const num = parseInt(views);
            if (isNaN(num)) return '0';
            if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
            if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
            return num.toString();
        }