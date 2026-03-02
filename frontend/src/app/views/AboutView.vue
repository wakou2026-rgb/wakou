<script setup>
import { useI18n } from "vue-i18n";
const { t } = useI18n();
</script>

<template>
  <div class="about-page">
    <!-- Intro Header -->
    <header class="page-header">
      <div class="header-inner">
        <img src="/logo-transparent.png" :alt="t('about.header_title')" class="header-logo" />
        <h1 class="header-title">{{ $t('about.header_title') }}</h1>
        <p class="header-subtitle">{{ $t('about.header_subtitle') }}</p>
      </div>
    </header>

    <!-- The Founder -->
    <section class="founder-section">
      <div class="container founder-layout">
        <!-- Image on left, refined with elegant frame -->
        <div class="founder-image-wrapper">
          <div class="image-frame">
            <img src="/Founder.png" :alt="t('about.founder_name') + ' - ' + t('about.header_title') + t('about.founder_role')" />
          </div>
        </div>

        <!-- Text on right, limited width for readability -->
        <div class="founder-text-wrapper">
          <div class="founder-title-block">
            <h2 class="founder-name">{{ $t('about.founder_name') }}</h2>
            <span class="founder-role">{{ $t('about.founder_role') }}</span>
          </div>
          
          <div class="bio-content">
            <p>{{ $t('about.bio_p1') }}</p>
            <p>{{ $t('about.bio_p2') }}</p>
            <p>{{ $t('about.bio_p3') }}</p>
            <p>{{ $t('about.bio_p4') }}</p>
            <p>{{ $t('about.bio_p5') }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- The Philosophy -->
    <section class="philosophy-section">
      <div class="container">
        <!-- Standalone Quote Area -->
        <div class="quote-block">
          <blockquote class="quote-text">
            {{ $t('about.quote') }}
          </blockquote>
          <p class="quote-sub">{{ $t('about.quote_sub') }}</p>
        </div>

        <!-- Details Grid -->
        <div class="core-layout">
          <!-- Left: Brand Focus -->
          <div class="focus-area">
            <span class="section-label">Brand Focus</span>
            <h3 class="area-title">{{ $t('about.brand_focus_label') }}</h3>
            <ul class="focus-list">
              <li>{{ $t('about.focus_1') }}</li>
              <li>{{ $t('about.focus_2') }}</li>
              <li>{{ $t('about.focus_3') }}</li>
              <li>{{ $t('about.focus_4') }}</li>
            </ul>
          </div>

          <!-- Right: Principles -->
          <div class="principles-area">
            <span class="section-label">Our Standards</span>
            <h3 class="area-title">{{ $t('about.standards_label') }}</h3>
            <div class="principles-grid">
              
              <div class="principle-item">
                <span class="p-num">01</span>
                <h4 class="p-title">{{ $t('about.principle_1_title') }}</h4>
                <p class="p-desc">{{ $t('about.principle_1_desc') }}</p>
              </div>

              <div class="principle-item">
                <span class="p-num">02</span>
                <h4 class="p-title">{{ $t('about.principle_2_title') }}</h4>
                <p class="p-desc">{{ $t('about.principle_2_desc') }}</p>
              </div>

              <div class="principle-item">
                <span class="p-num">03</span>
                <h4 class="p-title">{{ $t('about.principle_3_title') }}</h4>
                <p class="p-desc">{{ $t('about.principle_3_desc') }}</p>
              </div>

              <div class="principle-item">
                <span class="p-num">04</span>
                <h4 class="p-title">{{ $t('about.principle_4_title') }}</h4>
                <p class="p-desc">{{ $t('about.principle_4_desc') }}</p>
              </div>

            </div>
          </div>
        </div>

        <div class="philosophy-closing">
          <p>
            {{ $t('about.closing').split('\n')[0] }}<br/>
            {{ $t('about.closing').split('\n')[1] }}
          </p>
        </div>
      </div>
    </section>

    <!-- Contact Section -->
    <section class="contact-section">
      <div class="container">
        <span class="section-label center">Contact Us</span>
        <h2 class="contact-title">{{ $t('about.contact_title') }}</h2>
        
        <div class="contact-links">
          <a href="mailto:wakou2026@gmail.com" class="contact-btn">
            <svg viewBox="0 0 24 24" aria-hidden="true" width="18" height="18">
              <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2Zm0 4-8 5-8-5V6l8 5 8-5v2Z" fill="currentColor"/>
            </svg>
            wakou2026@gmail.com
          </a>
          <a href="https://www.instagram.com/wakou_vintage_select?igsh=MWFzZzIzcDltamVpZA%3D%3D&utm_source=qr" target="_blank" rel="noopener noreferrer" class="contact-btn">
            <svg viewBox="0 0 24 24" aria-hidden="true" width="18" height="18">
              <path d="M7.5 2h9A5.5 5.5 0 0 1 22 7.5v9a5.5 5.5 0 0 1-5.5 5.5h-9A5.5 5.5 0 0 1 2 16.5v-9A5.5 5.5 0 0 1 7.5 2Zm0 2A3.5 3.5 0 0 0 4 7.5v9A3.5 3.5 0 0 0 7.5 20h9a3.5 3.5 0 0 0 3.5-3.5v-9A3.5 3.5 0 0 0 16.5 4h-9Zm10.75 1.5a1.25 1.25 0 1 1 0 2.5 1.25 1.25 0 0 1 0-2.5ZM12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10Zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z" fill="currentColor"/>
            </svg>
            @wakou_vintage_select
          </a>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* Base Reset & Variables */
.about-page {
  --color-primary: var(--ink-900);
  --color-secondary: var(--ink-700);
  --color-accent: var(--accent-500);
  --color-bg: var(--paper-100);
  --color-bg-alt: var(--paper-200);
  --color-border: var(--paper-300);
  --font-serif: var(--font-serif);
  --font-sans: var(--font-sans);
  
  background-color: var(--color-bg);
  color: var(--color-primary);
  line-height: 1.6;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

/* Typography Utilities */
.section-label {
  font-size: 0.75rem;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: var(--color-accent);
  display: block;
  margin-bottom: 1rem;
}
.section-label.center {
  text-align: center;
}

/* Page Header */
.page-header {
  padding: 8rem 2rem 5rem;
  text-align: center;
}
.header-logo {
  height: 60px;
  width: auto;
  margin: 0 auto 1.5rem;
  display: block;
  opacity: 0.95;
}
.header-title {
  font-family: var(--font-serif);
  font-size: 2.25rem;
  letter-spacing: 0.25em;
  margin: 0 0 0.5rem;
  color: var(--color-primary);
  font-weight: 500;
}
.header-subtitle {
  font-size: 0.8rem;
  letter-spacing: 0.4em;
  color: var(--color-secondary);
  text-transform: uppercase;
  margin: 0;
}

/* Founder Section - Editorial Layout */
.founder-section {
  padding-bottom: 8rem;
}
.founder-layout {
  display: grid;
  grid-template-columns: 5fr 7fr;
  gap: 6rem;
  align-items: center;
}
.image-frame {
  position: relative;
  padding-bottom: 1.5rem;
  padding-right: 1.5rem;
}
.image-frame::after {
  content: '';
  position: absolute;
  right: 0;
  bottom: 0;
  width: 90%;
  height: 90%;
  border: 1px solid var(--color-accent);
  z-index: 0;
}
.image-frame img {
  width: 100%;
  aspect-ratio: 3/4;
  object-fit: cover;
  position: relative;
  z-index: 1;
  box-shadow: 0 20px 40px rgba(0,0,0,0.06);
}

.founder-title-block {
  margin-bottom: 2.5rem;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 1.5rem;
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 1rem;
}
.founder-name {
  font-family: var(--font-serif);
  font-size: 2.75rem;
  color: var(--color-primary);
  margin: 0;
  letter-spacing: 0.1em;
  font-weight: 500;
}
.founder-role {
  font-size: 1rem;
  color: var(--color-accent);
  letter-spacing: 0.15em;
}

.bio-content {
  max-width: 580px;
}
.bio-content p {
  color: var(--color-secondary);
  line-height: 2.1;
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
  text-align: justify;
}
.bio-content p:last-child {
  margin-bottom: 0;
}

/* Philosophy Section */
.philosophy-section {
  background-color: var(--color-bg-alt);
  padding: 8rem 0;
  position: relative;
}
.quote-block {
  text-align: center;
  max-width: 800px;
  margin: 0 auto 6rem;
}
.quote-text {
  font-family: var(--font-serif);
  font-size: 2rem;
  color: var(--color-primary);
  line-height: 1.7;
  font-style: italic;
  margin: 0 0 2rem;
}
.quote-sub {
  color: var(--color-secondary);
  font-size: 1rem;
  letter-spacing: 0.1em;
  margin: 0;
}

.core-layout {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 6rem;
}
.area-title {
  font-family: var(--font-serif);
  font-size: 1.75rem;
  color: var(--color-primary);
  margin: 0 0 3rem;
  font-weight: 500;
  letter-spacing: 0.05em;
}

/* Brand Focus List */
.focus-list {
  list-style: none;
  padding: 0;
  margin: 0;
  border-top: 1px solid var(--color-border);
}
.focus-list li {
  padding: 1.5rem 0;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-primary);
  font-size: 1.05rem;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
}
.focus-list li::before {
  content: '✦';
  color: var(--color-accent);
  margin-right: 1.25rem;
  font-size: 0.8rem;
}

/* Principles Grid */
.principles-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4rem 3rem;
}
.principle-item {
  position: relative;
}
.p-num {
  font-family: var(--font-serif);
  font-size: 2.5rem;
  color: var(--color-border);
  display: block;
  line-height: 1;
  margin-bottom: 1.25rem;
}
.p-title {
  font-size: 1.15rem;
  color: var(--color-primary);
  margin: 0 0 1rem;
  letter-spacing: 0.05em;
  font-weight: 500;
}
.p-desc {
  color: var(--color-secondary);
  line-height: 1.9;
  font-size: 0.95rem;
  margin: 0;
}

/* Closing Quote */
.philosophy-closing {
  text-align: center;
  margin-top: 6rem;
  padding-top: 6rem;
  border-top: 1px solid var(--color-border);
}
.philosophy-closing p {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  color: var(--color-secondary);
  line-height: 2;
  font-style: italic;
  margin: 0;
}

/* Contact Section */
.contact-section {
  padding: 8rem 0;
  text-align: center;
}
.contact-title {
  font-family: var(--font-serif);
  font-size: 2.25rem;
  color: var(--color-primary);
  margin: 0 0 4rem;
  font-weight: 500;
  letter-spacing: 0.1em;
}
.contact-links {
  display: flex;
  justify-content: center;
  gap: 2rem;
  flex-wrap: wrap;
}
.contact-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 2.5rem;
  border: 1px solid var(--color-border);
  color: var(--color-primary);
  text-decoration: none;
  font-size: 0.9rem;
  letter-spacing: 0.1em;
  transition: all 0.4s ease;
  background: transparent;
}
.contact-btn:hover {
  border-color: var(--color-primary);
  background-color: var(--color-primary);
  color: var(--color-bg);
}

/* Responsive */
@media (max-width: 1024px) {
  .founder-layout {
    grid-template-columns: 1fr;
    gap: 4rem;
  }
  .image-frame {
    max-width: 480px;
    margin: 0 auto;
  }
  .founder-title-block {
    justify-content: center;
    text-align: center;
  }
  .bio-content {
    max-width: 100%;
  }
  .core-layout {
    grid-template-columns: 1fr;
    gap: 5rem;
  }
}

@media (max-width: 768px) {
  .page-header {
    padding: 6rem 2rem 3rem;
  }
  .header-title {
    font-size: 1.75rem;
  }
  .quote-text {
    font-size: 1.5rem;
  }
  .principles-grid {
    grid-template-columns: 1fr;
    gap: 3rem;
  }
  .contact-links {
    flex-direction: column;
    align-items: center;
  }
  .contact-btn {
    width: 100%;
    max-width: 320px;
    justify-content: center;
  }
}
</style>
