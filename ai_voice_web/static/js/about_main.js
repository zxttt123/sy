document.addEventListener('DOMContentLoaded', () => {
  // 禁用自定义光标初始化
  // initCustomCursor();

  // 初始化导航栏滚动效果
  initScrollHeader();

  // 初始化汉堡菜单
  initHamburgerMenu();

  // 初始化GSAP动画
  initGSAPAnimations();

  // 初始化浮动元素
  initFloatingElements();

  // 初始化数字计数器动画
  initCounters();

  // 滚动到顶部按钮
  initScrollToTop();

  // 添加新的苹果风格效果
  initAppleStyleParallax();
  initButtonHoverEffects();
  initSmoothScrolling();
  addNeumorphismShadows();
  
  // 添加页面加载过渡效果
  const loadingOverlay = document.createElement('div');
  loadingOverlay.className = 'loading-overlay';
  document.body.appendChild(loadingOverlay);
  
  // 页面加载完成后淡出过渡层
  setTimeout(() => {
    gsap.to(loadingOverlay, {
      opacity: 0,
      duration: 0.8,
      ease: 'power2.out',
      onComplete: () => {
        loadingOverlay.remove();
      }
    });
  }, 500);
  
  // 添加加载过渡样式
  const overlayStyle = document.createElement('style');
  overlayStyle.textContent = `
    .loading-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: var(--background);
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  `;
  document.head.appendChild(overlayStyle);
});

// 保留但不使用自定义光标函数
function initCustomCursor() {
  // 函数保留但不执行任何操作
  return;
}

// 导航栏滚动效果
function initScrollHeader() {
  const header = document.querySelector('header');
  const scrollThreshold = 50;

  if (!header) return;

  window.addEventListener('scroll', () => {
    if (window.scrollY > scrollThreshold) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  });

  // 导航链接的激活状态
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-links a');

  window.addEventListener('scroll', () => {
    let current = '';
    const scrollPosition = window.scrollY + 200;

    sections.forEach(section => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.offsetHeight;
      
      if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
        current = section.getAttribute('id');
      }
    });

    navLinks.forEach(link => {
      link.classList.remove('active');
      if (link.getAttribute('href') === `#${current}`) {
        link.classList.add('active');
      }
    });
  });
}

// 汉堡菜单交互
function initHamburgerMenu() {
  const hamburger = document.querySelector('.hamburger');
  const nav = document.querySelector('nav');
  
  if (!hamburger || !nav) return;

  hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('active');
    nav.classList.toggle('active');
  });

  // 点击链接后关闭菜单
  const navLinks = document.querySelectorAll('.nav-links a');
  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      if (hamburger.classList.contains('active')) {
        hamburger.classList.remove('active');
        nav.classList.remove('active');
      }
    });
  });
}

// GSAP动画初始化
function initGSAPAnimations() {
  // 检查GSAP是否加载
  if (typeof gsap === 'undefined') {
    console.warn('GSAP library not loaded');
    return;
  }

  // 注册ScrollTrigger插件
  if (gsap.registerPlugin && typeof ScrollTrigger !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
  }

  // 页面加载动画
  const tl = gsap.timeline();
  
  tl.to('.slide-in-left', {
    x: 0,
    opacity: 1,
    duration: 0.8,
    stagger: 0.2,
    ease: 'power2.out'
  });
  
  tl.to('.slide-in-bottom', {
    y: 0,
    opacity: 1,
    duration: 0.8,
    stagger: 0.2,
    ease: 'power2.out'
  }, '-=0.4');
  
  tl.to('.fade-in', {
    opacity: 1,
    duration: 1,
    ease: 'power2.out'
  }, '-=0.6');

  // 滚动触发动画
  gsap.utils.toArray('[data-aos]').forEach(element => {
    const animation = element.getAttribute('data-aos');
    const delay = element.getAttribute('data-aos-delay') || 0;
    
    let animProps = {
      opacity: 0,
      y: 30,
      duration: 0.8,
      ease: 'power2.out'
    };
    
    if (animation === 'fade-up') {
      animProps = { ...animProps };
    } else if (animation === 'fade-down') {
      animProps.y = -30;
    } else if (animation === 'fade-left') {
      animProps.y = 0;
      animProps.x = -30;
    } else if (animation === 'fade-right') {
      animProps.y = 0;
      animProps.x = 30;
    }
    
    ScrollTrigger.create({
      trigger: element,
      start: 'top 80%',
      onEnter: () => {
        setTimeout(() => {
          gsap.to(element, {
            opacity: 1,
            y: 0,
            x: 0,
            duration: animProps.duration,
            ease: animProps.ease
          });
        }, delay);
      }
    });
  });

  // 特性卡片动画
  const featureCards = document.querySelectorAll('.feature-card');
  featureCards.forEach((card, index) => {
    ScrollTrigger.create({
      trigger: card,
      start: 'top 85%',
      onEnter: () => {
        gsap.to(card, {
          y: 0,
          opacity: 1,
          duration: 0.6,
          delay: index * 0.1
        });
      }
    });
  });

  // 流程步骤动画
  const processSteps = document.querySelectorAll('.process-step');
  processSteps.forEach((step, index) => {
    ScrollTrigger.create({
      trigger: step,
      start: 'top 85%',
      onEnter: () => {
        gsap.to(step, {
          y: 0,
          opacity: 1,
          duration: 0.6,
          delay: index * 0.15
        });
      }
    });
  });
}

// 修改浮动元素效果函数
function initFloatingElements() {
  const floatElements = document.querySelectorAll('.float-element');
  
  if (floatElements.length === 0) return;
  
  // 检查是否为移动设备
  const isMobile = window.innerWidth <= 992;

  // 调整第三个元素（机器人图标）的位置，确保其不被波浪线遮挡
  if (!isMobile && floatElements[2]) {
    // 确保机器人图标不会太靠近底部
    const robotIcon = floatElements[2];
    if (window.innerHeight < 800) {
      // 在较小的屏幕高度上，进一步调整位置
      robotIcon.style.bottom = '30%';
    }
  }

  floatElements.forEach((element, index) => {
    const speed = element.getAttribute('data-speed') || 0.03;
    
    // 针对不同设备设置不同的动画效果
    if (isMobile) {
      // 移动设备上使用更简单的上下浮动效果
      gsap.to(element, {
        y: '-=10',
        duration: 1.5 + Math.random() * 1,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut'
      });
    } else {
      // 桌面设备上使用更复杂的随机浮动效果
      // 对于机器人图标，限制垂直方向的浮动范围，防止与波浪线重叠
      const xPos = Math.random() * 20 - 10;
      const yPos = index === 2 ? (Math.random() * 10 - 5) : (Math.random() * 20 - 10);
      
      gsap.to(element, {
        y: yPos,
        x: xPos,
        duration: 3 + Math.random() * 2,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut'
      });
    }
    
    // 悬停效果保持不变
    element.addEventListener('mouseenter', () => {
      gsap.to(element, {
        scale: 1.2,
        duration: 0.5
      });
    });
    
    element.addEventListener('mouseleave', () => {
      gsap.to(element, {
        scale: 1,
        duration: 0.5
      });
    });
  });
  
  // 监听窗口大小变化，重新定位浮动元素
  window.addEventListener('resize', () => {
    // 简单的防抖处理
    clearTimeout(window.resizeTimer);
    window.resizeTimer = setTimeout(() => {
      // 重新初始化浮动元素
      if ((window.innerWidth <= 992 && !isMobile) || 
          (window.innerWidth > 992 && isMobile)) {
        // 重新加载页面以应用新的布局
        // 或者可以杀掉当前动画并重新初始化
        floatElements.forEach(element => {
          gsap.killTweensOf(element);
        });
        initFloatingElements();
      }
    }, 250);
  });
}

// 数字计数器动画
function initCounters() {
  const counters = document.querySelectorAll('.counter');
  
  if (counters.length === 0) return;

  counters.forEach(counter => {
    const target = parseFloat(counter.textContent);
    counter.textContent = '0';
    
    const counterAnimation = () => {
      const startValue = 0;
      const duration = 2000;
      const startTime = performance.now();
      
      const updateCounter = (currentTime) => {
        const elapsedTime = currentTime - startTime;
        if (elapsedTime < duration) {
          const progress = elapsedTime / duration;
          const currentValue = Math.round(progress * target);
          counter.textContent = currentValue + (counter.textContent.includes('%') ? '%' : '+');
          requestAnimationFrame(updateCounter);
        } else {
          counter.textContent = target + (counter.textContent.includes('%') ? '%' : '+');
        }
      };
      
      requestAnimationFrame(updateCounter);
    };
    
    // 使用ScrollTrigger来触发动画
    ScrollTrigger.create({
      trigger: counter,
      start: 'top 80%',
      onEnter: counterAnimation,
      once: true
    });
  });
}

// 滚动到顶部按钮
function initScrollToTop() {
  // 创建滚动到顶部按钮
  const scrollTopBtn = document.createElement('button');
  scrollTopBtn.className = 'scroll-top-btn';
  scrollTopBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
  document.body.appendChild(scrollTopBtn);
  
  // 添加样式
  const style = document.createElement('style');
  style.textContent = `
    .scroll-top-btn {
      position: fixed;
      bottom: 30px;
      right: 30px;
      width: 50px;
      height: 50px;
      border-radius: 50%;
      background-color: var(--primary-color);
      color: white;
      border: none;
      box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s ease;
      z-index: 99;
    }
    
    .scroll-top-btn.visible {
      opacity: 1;
      visibility: visible;
    }
    
    .scroll-top-btn:hover {
      background-color: var(--primary-dark);
      transform: translateY(-3px);
    }
  `;
  document.head.appendChild(style);
  
  // 显示/隐藏按钮
  window.addEventListener('scroll', () => {
    if (window.pageYOffset > 300) {
      scrollTopBtn.classList.add('visible');
    } else {
      scrollTopBtn.classList.remove('visible');
    }
  });
  
  // 点击事件
  scrollTopBtn.addEventListener('click', () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });
}

// 修改视差效果函数中浮动元素的处理方式
function initAppleStyleParallax() {
  // 特性卡片悬停视差效果
  const cards = document.querySelectorAll('.feature-card');
  
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      const deltaX = (x - centerX) / centerX;
      const deltaY = (y - centerY) / centerY;
      
      // 旋转效果
      gsap.to(card, {
        rotationY: deltaX * 5,
        rotationX: -deltaY * 5,
        transformPerspective: 1000,
        duration: 0.5,
        ease: 'power2.out'
      });
      
      // 图标移动效果
      const icon = card.querySelector('.icon-circle');
      if (icon) {
        gsap.to(icon, {
          x: deltaX * 10,
          y: deltaY * 10,
          duration: 0.5,
          ease: 'power2.out'
        });
      }
    });
    
    card.addEventListener('mouseleave', () => {
      gsap.to(card, {
        rotationY: 0,
        rotationX: 0,
        duration: 0.6,
        ease: 'elastic.out(1, 0.5)'
      });
      
      const icon = card.querySelector('.icon-circle');
      if (icon) {
        gsap.to(icon, {
          x: 0,
          y: 0,
          duration: 0.6,
          ease: 'elastic.out(1, 0.5)'
        });
      }
    });
  });
  
  // 英雄区域视差效果
  const hero = document.querySelector('.hero');
  if (hero) {
    window.addEventListener('mousemove', (e) => {
      // 只在非移动设备上应用鼠标视差效果
      if (window.innerWidth <= 992) return;
      
      const { clientX, clientY } = e;
      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;
      
      const deltaX = (clientX - centerX) / centerX;
      const deltaY = (clientY - centerY) / centerY;
      
      const heroImage = document.querySelector('.hero-image img');
      const floatElements = document.querySelectorAll('.float-element');
      
      if (heroImage) {
        gsap.to(heroImage, {
          rotationY: -deltaX * 3,
          rotationX: deltaY * 3,
          duration: 1,
          ease: 'power2.out'
        });
      }
      
      floatElements.forEach(element => {
        const speed = parseFloat(element.getAttribute('data-speed')) || 0.03;
        gsap.to(element, {
          x: deltaX * 30 * speed * 10,
          y: deltaY * 30 * speed * 10,
          duration: 1,
          ease: 'power2.out'
        });
      });
    });
  }
  
  // 添加滚动视差效果
  const parallaxElements = document.querySelectorAll('.section-header, .demo-card, .about-image');
  
  parallaxElements.forEach(element => {
    ScrollTrigger.create({
      trigger: element,
      start: 'top bottom',
      end: 'bottom top',
      scrub: 1,
      onUpdate: (self) => {
        const progress = self.progress;
        element.style.transform = `translateY(${progress * -50}px)`;
      }
    });
  });
}

// 修改按钮悬停效果函数增加对btn-cta的支持
function initButtonHoverEffects() {
  const buttons = document.querySelectorAll('.btn');
  
  buttons.forEach(button => {
    button.addEventListener('mouseenter', () => {
      if (button.classList.contains('btn-primary')) {
        gsap.to(button, {
          scale: 1.05,
          duration: 0.3,
          ease: 'power2.out',
          boxShadow: '0 8px 20px rgba(0, 113, 227, 0.3)'
        });
      } else if (button.classList.contains('btn-outline')) {
        gsap.to(button, {
          scale: 1.05,
          duration: 0.3,
          ease: 'power2.out',
          backgroundColor: 'rgba(0, 113, 227, 0.05)'
        });
      } else if (button.classList.contains('btn-cta')) {
        gsap.to(button, {
          scale: 1.05,
          duration: 0.3,
          ease: 'power2.out',
          boxShadow: '0 8px 20px rgba(255, 97, 0, 0.3)'
        });
      }
    });
    
    button.addEventListener('mouseleave', () => {
      let bgColor = 'transparent';
      if (button.classList.contains('btn-primary')) {
        bgColor = 'var(--primary-color)';
      } else if (button.classList.contains('btn-cta')) {
        bgColor = 'var(--accent-color)';
      }
      
      gsap.to(button, {
        scale: 1,
        duration: 0.3,
        ease: 'power2.out',
        boxShadow: 'none',
        backgroundColor: bgColor
      });
    });
  });
  
  // 移除波纹效果相关代码
}

// 初始化平滑滚动
function initSmoothScrolling() {
  // 平滑滚动链接处理
  const scrollLinks = document.querySelectorAll('a[href^="#"]');
  
  scrollLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      
      const targetId = link.getAttribute('href');
      if (targetId === '#') return;
      
      const targetElement = document.querySelector(targetId);
      if (!targetElement) return;
      
      const headerOffset = 80;
      const elementPosition = targetElement.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
      
      // 使用GSAP进行更平滑的滚动
      gsap.to(window, {
        duration: 1,
        scrollTo: {
          y: offsetPosition,
          autoKill: false
        },
        ease: 'power3.out'
      });
    });
  });
  
  // 添加滚动指示器
  const scrollIndicator = document.createElement('div');
  scrollIndicator.className = 'scroll-indicator';
  document.body.appendChild(scrollIndicator);
  
  // 添加样式
  const style = document.createElement('style');
  style.textContent = `
    .scroll-indicator {
      position: fixed;
      top: 0;
      left: 0;
      height: 3px;
      background: linear-gradient(90deg, var(--primary-color), var(--primary-light));
      z-index: 9999;
      width: 0%;
      transition: width 0.1s;
    }
  `;
  document.head.appendChild(style);
  
  // 更新滚动指示器
  window.addEventListener('scroll', () => {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrolled = (scrollTop / scrollHeight) * 100;
    
    scrollIndicator.style.width = `${scrolled}%`;
  });
}

// 添加拟物态阴影效果
function addNeumorphismShadows() {
  const elements = document.querySelectorAll('.feature-card, .demo-card, .process-step .step-icon, .social-icons a');
  
  elements.forEach(element => {
    element.addEventListener('mouseenter', () => {
      gsap.to(element, {
        boxShadow: '10px 10px 20px rgba(0, 0, 0, 0.05), -10px -10px 20px rgba(255, 255, 255, 0.8)',
        duration: 0.3
      });
    });
    
    element.addEventListener('mouseleave', () => {
      gsap.to(element, {
        boxShadow: 'var(--shadow)',
        duration: 0.3
      });
    });
  });
}

// 添加滚动时的视差效果
window.addEventListener('scroll', () => {
  const scrollPosition = window.pageYOffset;
  const heroContent = document.querySelector('.hero-content');
  const heroImage = document.querySelector('.hero-image');
  
  if (heroContent && heroImage) {
    heroContent.style.transform = `translateY(${scrollPosition * 0.1}px)`;
    heroImage.style.transform = `translateY(${scrollPosition * 0.05}px) rotateY(-5deg) rotateX(5deg)`;
  }
});

// 在链接上添加平滑滚动
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    
    const targetId = this.getAttribute('href');
    if (targetId === '#') return;
    
    const targetElement = document.querySelector(targetId);
    if (!targetElement) return;
    
    const headerOffset = 80;
    const elementPosition = targetElement.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
    
    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
  });
});

// 响应式图片加载
function loadResponsiveImages() {
  const images = document.querySelectorAll('img[data-src]');
  
  images.forEach(img => {
    const src = img.getAttribute('data-src');
    img.setAttribute('src', src);
    img.onload = () => {
      img.removeAttribute('data-src');
    };
  });
}

// 页面加载完成后加载图片
window.addEventListener('load', loadResponsiveImages);
