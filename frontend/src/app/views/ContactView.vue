<script setup>
import { useI18n } from "vue-i18n";
const { t } = useI18n();
</script>

<template>
  <div class="contact-page container">
    <section class="contact-shell panel">
      <aside class="contact-title">
        <p class="eyebrow">Contact</p>
        <h1 class="page-title">{{ $t('contact.title') }}</h1>
        <p class="page-meta">{{ $t('contact.subtitle') }}</p>
      </aside>

      <div class="contact-content">
        <article class="contact-row">
          <p class="row-head">Email</p>
          <div>
            <a class="line-link" href="mailto:wakou2026@gmail.com">wakou2026@gmail.com</a>
            <p class="hint">{{ $t('contact.hours_hint') }}</p>
          </div>
        </article>

        <article class="contact-row">
          <p class="row-head">Instagram</p>
          <div>
            <a class="line-link" href="https://www.instagram.com/" target="_blank" rel="noopener noreferrer">@wakou_select</a>
            <p class="hint">{{ $t('contact.ig_hint') }}</p>
          </div>
        </article>

        <article class="contact-row">
          <p class="row-head">YouTube</p>
          <div>
            <a class="line-link" href="https://www.youtube.com/" target="_blank" rel="noopener noreferrer">Wakou Vintage Select</a>
            <p class="hint">{{ $t('contact.yt_hint') }}</p>
          </div>
        </article>

        <article class="contact-row">
          <p class="row-head">Inquiry</p>
          <div>
            <p class="hint">{{ $t('contact.inquiry_hint') }}</p>
            <RouterLink class="btn btn-primary" to="/collections">{{ $t('contact.go_gallery') }}</RouterLink>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.contact-page {
  max-width: 1200px;
}

.contact-shell {
  display: grid;
  gap: 2rem;
  grid-template-columns: minmax(220px, 320px) minmax(0, 1fr);
}

.contact-title {
  border-right: 1px solid var(--paper-300);
  padding-right: 1.4rem;
}

.contact-content {
  display: grid;
  gap: 0.95rem;
}

.contact-row {
  border-bottom: 1px solid var(--paper-300);
  column-gap: 1rem;
  display: grid;
  grid-template-columns: 120px 1fr;
  padding-bottom: 0.8rem;
}

.row-head,
.hint {
  margin: 0;
}

.row-head {
  color: var(--ink-500);
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.line-link {
  color: var(--ink-900);
  display: inline-block;
  margin-bottom: 0.3rem;
  letter-spacing: 0.05em;
  text-decoration: underline;
  text-underline-offset: 0.2rem;
}

.hint {
  color: var(--ink-700);
}

@media (max-width: 900px) {
  .contact-shell,
  .contact-row {
    grid-template-columns: 1fr;
  }

  .contact-title {
    border-right: 0;
    border-bottom: 1px solid var(--paper-300);
    padding-bottom: 1rem;
    padding-right: 0;
  }
}
</style>
