// Tube Download JPRO — Interactive Landing Page Script

document.addEventListener('DOMContentLoaded', () => {
  // 1. Screenshot Showcase Tabs
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');

      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    });
  });

  // 2. FAQ Accordion
  const faqQuestions = document.querySelectorAll('.faq-question');
  faqQuestions.forEach(question => {
    question.addEventListener('click', () => {
      const item = question.closest('.faq-item');
      const isOpen = item.classList.contains('open');

      // Close all items
      document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));

      // If it wasn't open, open it
      if (!isOpen) {
        item.classList.add('open');
      }
    });
  });

  // 3. Legal / Policy Modals
  const modalOverlay = document.getElementById('modal-overlay');
  const modalTitle = document.getElementById('modal-title');
  const modalBody = document.getElementById('modal-body');
  const modalClose = document.getElementById('modal-close');

  const policies = {
    refund: {
      title: '14-Day Money-Back Guarantee & Refund Policy',
      content: `
        <p>At Tube Download JPRO, customer satisfaction is our highest priority. We offer an unconditional <strong>14-Day Money-Back Guarantee</strong> on all Pro licenses (Monthly, 3-Month, 1-Year, and Lifetime).</p>
        <h4>Eligibility for Refunds:</h4>
        <ul>
          <li>You purchased your license within the last 14 days.</li>
          <li>The software failed to operate as advertised on your supported Windows system and our support team could not resolve the issue within 48 hours.</li>
        </ul>
        <h4>How to Request:</h4>
        <p>Simply email our support desk at <a href="mailto:jprosoftware.support@gmail.com" style="color:#00F2FE;">jprosoftware.support@gmail.com</a> with your order number or license key. Refunds are processed back to your original payment method via Lemon Squeezy within 3–5 business days.</p>
      `
    },
    terms: {
      title: 'Terms of Service',
      content: `
        <p>By downloading or purchasing Tube Download JPRO, you agree to the following terms:</p>
        <h4>License Grant:</h4>
        <p>A Pro license grants non-transferable access for use on 1 active Windows device. Lifetime licenses include permanent usage and ongoing core engine updates.</p>
        <h4>Fair Use & Compliance:</h4>
        <p>Tube Download JPRO is a media utility tool. Users are strictly responsible for complying with the terms of service of third-party platforms and respecting copyright laws in their respective jurisdictions. You may only download content that you own or have explicit permission to archive.</p>
      `
    },
    privacy: {
      title: 'Privacy Policy',
      content: `
        <p>We respect your digital privacy. Tube Download JPRO is built with local-first processing:</p>
        <ul>
          <li><strong>No Activity Tracking:</strong> We never log your downloaded links, search queries, or media files. All downloads occur directly between your device and the media servers.</li>
          <li><strong>Zero Telemetry Selling:</strong> We do not sell or monetize user data.</li>
          <li><strong>Payment Processing:</strong> Payments are handled securely by Lemon Squeezy (PCI-DSS compliant). We never see or store your credit card details.</li>
        </ul>
      `
    }
  };

  document.querySelectorAll('[data-modal]').forEach(trigger => {
    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      const type = trigger.getAttribute('data-modal');
      const data = policies[type];
      if (data && modalOverlay) {
        modalTitle.textContent = data.title;
        modalBody.innerHTML = data.content;
        modalOverlay.classList.add('active');
      }
    });
  });

  if (modalClose) {
    modalClose.addEventListener('click', () => {
      modalOverlay.classList.remove('active');
    });
  }

  if (modalOverlay) {
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) {
        modalOverlay.classList.remove('active');
      }
    });
  }

  // 4. Smooth scrolling for hash links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({
          behavior: 'smooth'
        });
      }
    });
  });
});
