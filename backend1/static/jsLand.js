function swishOnScroll() {
    var elements = document.querySelectorAll('.text');
    var windowHeight = window.innerHeight;
  
    elements.forEach(function(element) {
      var elementPosition = element.getBoundingClientRect().top;
  
      if (elementPosition - windowHeight <= 0) {
        element.classList.add('show');
      }
    });
  }
  
  window.addEventListener('scroll', swishOnScroll);


  