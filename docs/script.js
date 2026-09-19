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
      title: 'Terms of Service & Legal Compliance',
      content: `
        <p>By downloading, installing, or purchasing Tube Download JPRO, you agree to the following terms and conditions:</p>
        <h4>1. Purpose &amp; Fair Use:</h4>
        <p>Tube Download JPRO is a media productivity and archival utility intended for personal backup, offline study, and creator editing workflows. Users are strictly responsible for complying with the terms of service of third-party platforms and respecting copyright laws in their respective jurisdictions. You may only download content that you own, have explicit creator permission to archive, or that is licensed under Creative Commons or public domain.</p>
        <h4>2. Commercial License Grant:</h4>
        <p>A Pro commercial license grants non-transferable access for use on 1 active Windows device. Lifetime licenses include permanent usage and ongoing core engine updates on the activated device. In the event of a computer change or hardware upgrade, users may contact support to rebind their activation.</p>
        <h4>3. Open-Source Attributions:</h4>
        <p>Tube Download JPRO incorporates open-source multimedia components in strict compliance with their licenses:</p>
        <ul>
          <li><strong>FFmpeg:</strong> Licensed under the GNU Lesser General Public License (LGPL) version 2.1 or later. FFmpeg is an open-source trademark of Fabrice Bellard. Source code and documentation are available at <a href="https://ffmpeg.org" target="_blank" style="color:#00F2FE;">ffmpeg.org</a>.</li>
          <li><strong>yt-dlp:</strong> Distributed under the Unlicense (Public Domain dedication). Source code and documentation are available at <a href="https://github.com/yt-dlp/yt-dlp" target="_blank" style="color:#00F2FE;">github.com/yt-dlp/yt-dlp</a>.</li>
          <li><strong>CustomTkinter:</strong> Licensed under the MIT License by Tom Schimansky.</li>
        </ul>
        <h4>4. DMCA &amp; Intellectual Property Notice:</h4>
        <p>We respect intellectual property rights. If you believe your copyrighted work is being infringed or if you are a copyright holder seeking inquiries, please contact our designated support address at <a href="mailto:jprosoftware.support@gmail.com" style="color:#00F2FE;">jprosoftware.support@gmail.com</a>. We will respond promptly to valid notices.</p>
        <h4>5. Disclaimer of Warranties:</h4>
        <p>The software is provided "AS IS", without warranty of any kind, express or implied. Under no circumstances shall the software developers be liable for any direct, indirect, incidental, or consequential damages resulting from the use or inability to use this utility.</p>
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
