// Function to fetch categories from the API
        async function fetchCategories() {
            try {
                const response = await fetch('/api/get-categories/'); // Fetch data from the API endpoint
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                const categories = await response.json(); // Parse the JSON response
                return categories;
            } catch (error) {
                console.error('Error fetching categories:', error);
                throw error; // Re-throw the error for handling in initializePage
            }
        }

        // Function to render categories
        function renderCategories(categories) {
            const categoriesList = document.getElementById('categoriesList');
            categoriesList.innerHTML = ''; // Clear the loading message

            categories.forEach(category => {
                // Construct the URL dynamically using the category ID
                const categoryUrl = `/departments/${category.id}/`;

                console.log('the ID is ', category.id);

                const categoryCard = `
                    <div class="col-md-6 col-lg-3" data-aos="fade-left" data-aos-delay="50">
                        <a href="${categoryUrl}">
                            <div class="field-card">
                                <h3 class="field-title">
                                    <i class="fa-solid fa-book-open"></i>
                                    ${category.name}
                                </h3>
                            </div>
                        </a>
                    </div>
                `;
                categoriesList.innerHTML += categoryCard; // Append the category card to the list
            });
        }

        // Initialize the page
        async function initializePage() {
            try {
                const categories = await fetchCategories(); // Fetch categories from the API
                renderCategories(categories); // Render the categories
            } catch (error) {
                const categoriesList = document.getElementById('categoriesList');
                categoriesList.innerHTML = `
                    <div class="col-12 text-center">
                        <p>Failed to load categories. Please try again later.</p>
                    </div>
                `;
            }
        }

        // Call initializePage when the page loads
        document.addEventListener('DOMContentLoaded', initializePage);
