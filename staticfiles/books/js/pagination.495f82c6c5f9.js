
      // Initialize AOS
      AOS.init({
        duration: 1000,
        once: true
      })
      
      // Navbar scroll effect
      window.addEventListener('scroll', function () {
        const navbar = document.querySelector('.navbar')
        if (window.scrollY > 50) {
          navbar.style.background = 'rgba(255, 255, 255, 0.95)'
        } else {
          navbar.style.background = 'white'
        }
      })
      
      document.addEventListener('DOMContentLoaded', function () {
        const slides = document.querySelectorAll('.testimonial-slide')
        const dots = document.querySelectorAll('.dot')
        const prevButton = document.querySelector('.prev-slide')
        const nextButton = document.querySelector('.next-slide')
        let currentSlide = 0
      
        function showSlide(n) {
          slides.forEach((slide) => slide.classList.remove('active'))
          dots.forEach((dot) => dot.classList.remove('active'))
      
          currentSlide = (n + slides.length) % slides.length
          slides[currentSlide].classList.add('active')
          dots[currentSlide].classList.add('active')
        }
      
        function nextSlide() {
          showSlide(currentSlide + 1)
        }
      
        function previousSlide() {
          showSlide(currentSlide - 1)
        }
      
        // Event listeners
        prevButton.addEventListener('click', previousSlide)
        nextButton.addEventListener('click', nextSlide)
      
        dots.forEach((dot, index) => {
          dot.addEventListener('click', () => showSlide(index))
        })
      
        // Auto-advance slides every 5 seconds
        setInterval(nextSlide, 5000)
      })
      
      document.getElementById('newsletterForm').addEventListener('submit', function (e) {
        e.preventDefault()
        const email = this.querySelector('input[type="email"]').value
      
        // Here you would typically send this to your backend
        console.log('Newsletter subscription for:', email)
      
        // Clear the input
        this.querySelector('input[type="email"]').value = ''
      
        // Show success message (you can enhance this)
        alert('Thank you for subscribing!')
      })
