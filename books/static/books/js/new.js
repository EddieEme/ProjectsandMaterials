class YouTubeManager {
    constructor(apiKey, channelId) {
        this.apiKey = apiKey;
        this.channelId = channelId;
        this.container = document.getElementById('videoContainer');
    }

    async init() {
        try {
            const videos = await this.fetchVideos();
            this.displayVideos(videos);
        } catch (error) {
            this.handleError(error);
        }
    }

    async fetchVideos() {
        // Fetch most viewed videos instead of latest uploads
        const videoItems = await this.getMostViewedVideos();
        if (!videoItems?.length) throw new Error('No videos found');

        // Get video statistics
        return await this.getVideoStatistics(videoItems);
    }

    async getMostViewedVideos() {
        const response = await fetch(
            `https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=${this.channelId}&order=viewCount&type=video&maxResults=3&key=${this.apiKey}`
        );

        if (!response.ok) {
            throw new Error(`Search API error: ${response.status}`);
        }

        const data = await response.json();
        return data.items;
    }

    async getVideoStatistics(videos) {
        const videoIds = videos.map(video => video.id.videoId).join(',');
        const response = await fetch(
            `https://www.googleapis.com/youtube/v3/videos?part=statistics&id=${videoIds}&key=${this.apiKey}`
        );

        if (!response.ok) {
            throw new Error(`Statistics API error: ${response.status}`);
        }

        const statsData = await response.json();

        // Combine video data with statistics
        return videos.map((video, index) => ({
            ...video,
            statistics: statsData.items[index]?.statistics || { viewCount: 0 }
        }));
    }

    displayVideos(videos) {
        this.container.innerHTML = ''; // Clear loading state

        videos.forEach(video => {
            const videoDate = new Date(video.snippet.publishedAt);
            const formattedDate = videoDate.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });

            // Use thumbnail from YouTube
            const thumbnailUrl = video.snippet.thumbnails.high?.url ||
                video.snippet.thumbnails.medium?.url ||
                video.snippet.thumbnails.default?.url;

            const videoHtml = `
                <div class="col-lg-4 col-md-6">
                    <article class="video-card">
                        <div class="video-wrapper">
                            <iframe 
                                src="https://www.youtube.com/embed/${video.id.videoId}"
                                title="${video.snippet.title}"
                                frameborder="0"
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowfullscreen
                            ></iframe>
                        </div>
                        <div class="video-content">
                            <span class="video-category">Most Viewed</span>
                            <h3 class="video-title">${this.sanitizeHTML(video.snippet.title)}</h3>
                            <div class="video-meta">
                                ${formattedDate} • ${this.formatViewCount(video.statistics.viewCount)} views
                            </div>
                            <p class="video-description">
                                ${this.sanitizeHTML(video.snippet.description.slice(0, 100))}...
                            </p>
                            <a href="https://www.youtube.com/watch?v=${video.id.videoId}" 
                               class="watch-more" 
                               target="_blank" 
                               rel="noopener noreferrer">
                                Watch on YouTube
                            </a>
                        </div>
                    </article>
                </div>
            `;
            this.container.innerHTML += videoHtml;
        });
    }

    handleError(error) {
        console.error('YouTube API Error:', error);
        this.container.innerHTML = `
            <div class="col-12">
                <div class="error-message">
                    <h3>Oops! Something went wrong</h3>
                    <p>We're having trouble loading the videos. Please try again later.</p>
                    <small>Error: ${this.sanitizeHTML(error.message)}</small>
                </div>
            </div>
        `;
    }

    sanitizeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    formatViewCount(views) {
        const num = parseInt(views);
        if (isNaN(num)) return '0';
        if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
        if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
        return num.toString();
    }
}

// Initialize YouTube manager when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const youTubeManager = new YouTubeManager(
        'AIzaSyDjt40GkdOQP1k1WCy_Ms7ci7Gt59bnDzU',  // Replace with your API key
        'UCaB3YPxB_eXqTcFdFo9CrCA' // Replace with your channel ID
    );
    youTubeManager.init();
});
