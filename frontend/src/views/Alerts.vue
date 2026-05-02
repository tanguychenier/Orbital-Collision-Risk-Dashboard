<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import InputNumber from 'primevue/inputnumber';
import Slider from 'primevue/slider';
import Message from 'primevue/message';
import HeaderBar from '@/components/HeaderBar.vue';
import FooterBar from '@/components/FooterBar.vue';
import { createAlertSubscription } from '@/api/alerts';
import { ApiClientError } from '@/api/client';
import {
  DEFAULT_THRESHOLD_KM,
  MAX_NORAD_IDS,
  MAX_THRESHOLD_KM,
  MIN_THRESHOLD_KM,
  type AlertFormError,
  validateAlertForm
} from '@/composables/useAlertForm';
import type { AlertSubscriptionCreated } from '@/api/types';

const draft = reactive({
  emailOrWebhookUrl: '',
  noradIdsRaw: '',
  thresholdKm: DEFAULT_THRESHOLD_KM
});

const submitting = ref(false);
const result = ref<AlertSubscriptionCreated | null>(null);
const submitError = ref<string | null>(null);
const validationErrors = ref<ReadonlyArray<AlertFormError>>([]);
const copied = ref(false);

const errorMessages: Record<AlertFormError, string> = {
  TARGET_REQUIRED: 'A webhook URL or email address is required.',
  TARGET_INVALID: 'Enter a valid https:// URL or email address.',
  NORAD_IDS_REQUIRED: 'List at least one NORAD catalog id.',
  NORAD_IDS_INVALID: 'NORAD ids must be positive integers, comma-separated.',
  NORAD_IDS_TOO_MANY: `At most ${MAX_NORAD_IDS} satellites per subscription.`,
  THRESHOLD_OUT_OF_RANGE: `Threshold must lie between ${MIN_THRESHOLD_KM} and ${MAX_THRESHOLD_KM} km.`
};

const visibleErrors = computed(() => validationErrors.value.map((code) => errorMessages[code]));

async function onSubmit(): Promise<void> {
  submitError.value = null;
  copied.value = false;
  const validation = validateAlertForm(draft);
  if (!validation.ok) {
    validationErrors.value = validation.errors;
    return;
  }
  validationErrors.value = [];
  submitting.value = true;
  try {
    result.value = await createAlertSubscription(validation.payload);
  } catch (err) {
    if (err instanceof ApiClientError) {
      submitError.value = err.detail;
    } else if (err instanceof Error) {
      submitError.value = err.message;
    } else {
      submitError.value = 'Subscription failed.';
    }
  } finally {
    submitting.value = false;
  }
}

async function copyManageUrl(): Promise<void> {
  if (result.value === null) return;
  try {
    await navigator.clipboard.writeText(result.value.manage_url);
    copied.value = true;
  } catch {
    copied.value = false;
  }
}

function resetForm(): void {
  result.value = null;
  copied.value = false;
  draft.emailOrWebhookUrl = '';
  draft.noradIdsRaw = '';
  draft.thresholdKm = DEFAULT_THRESHOLD_KM;
}
</script>

<template>
  <div class="flex flex-col flex-1 min-h-screen">
    <HeaderBar />

    <main class="flex-1 mx-auto w-full max-w-2xl px-4 py-6 sm:py-10" data-testid="alerts-view">
      <h2 class="text-xl sm:text-2xl font-semibold tracking-tight mb-2">Conjunction alerts</h2>
      <p class="text-sm text-white/70 mb-6">
        Get a Discord (or webhook) notification, or an email, every time a close approach drops
        below your threshold for any of the satellites you watch. No accounts, no logins. The manage
        URL we hand back is the only key.
      </p>

      <form
        v-if="result === null"
        class="space-y-5"
        data-testid="alerts-form"
        @submit.prevent="onSubmit"
      >
        <div>
          <label for="alert-target" class="block text-sm font-medium mb-1">
            Webhook URL or email
          </label>
          <InputText
            id="alert-target"
            v-model="draft.emailOrWebhookUrl"
            class="w-full"
            placeholder="https://discord.com/api/webhooks/..."
            data-testid="alerts-target"
            autocomplete="off"
          />
          <p class="text-xs text-white/50 mt-1">
            Discord webhook URLs are accepted as-is; any RFC-compatible email address works too.
          </p>
        </div>

        <div>
          <label for="alert-norad" class="block text-sm font-medium mb-1">
            NORAD catalog ids
          </label>
          <InputText
            id="alert-norad"
            v-model="draft.noradIdsRaw"
            class="w-full"
            placeholder="25544, 33591, 47967"
            data-testid="alerts-norad-ids"
            autocomplete="off"
          />
          <p class="text-xs text-white/50 mt-1">
            Comma-separated NORAD ids of the satellites you watch (max {{ MAX_NORAD_IDS }}).
          </p>
        </div>

        <div>
          <label for="alert-threshold" class="block text-sm font-medium mb-2">
            Miss distance threshold (km)
          </label>
          <div class="flex items-center gap-3">
            <Slider
              v-model="draft.thresholdKm"
              :min="MIN_THRESHOLD_KM"
              :max="MAX_THRESHOLD_KM"
              :step="0.1"
              class="flex-1"
              data-testid="alerts-threshold"
            />
            <InputNumber
              v-model="draft.thresholdKm"
              :min="MIN_THRESHOLD_KM"
              :max="MAX_THRESHOLD_KM"
              :min-fraction-digits="1"
              :max-fraction-digits="1"
              :step="0.1"
              show-buttons
              class="w-32"
              data-testid="alerts-threshold-input"
            />
          </div>
          <p class="text-xs text-white/50 mt-1">
            We notify you when a predicted close approach is at or below this distance.
          </p>
        </div>

        <div v-if="visibleErrors.length > 0" class="space-y-1" data-testid="alerts-form-errors">
          <Message v-for="msg in visibleErrors" :key="msg" severity="error" :closable="false">{{
            msg
          }}</Message>
        </div>

        <Message
          v-if="submitError !== null"
          severity="error"
          :closable="false"
          data-testid="alerts-submit-error"
          >{{ submitError }}</Message
        >

        <div class="flex justify-end">
          <Button
            type="submit"
            :loading="submitting"
            data-testid="alerts-submit"
            label="Subscribe"
            icon="pi pi-bell"
          />
        </div>
      </form>

      <section v-else class="space-y-4" data-testid="alerts-success">
        <Message severity="success" :closable="false">
          Subscription created. You will receive a notification the next time a conjunction below
          your threshold touches one of the satellites you watch.
        </Message>

        <div>
          <label for="alert-manage-url" class="block text-sm font-medium mb-1">
            Your manage URL
          </label>
          <div class="flex items-stretch gap-2">
            <InputText
              id="alert-manage-url"
              :model-value="result.manage_url"
              readonly
              class="flex-1 font-mono text-xs"
              data-testid="alerts-manage-url"
            />
            <Button
              :icon="copied ? 'pi pi-check' : 'pi pi-copy'"
              severity="secondary"
              :label="copied ? 'Copied' : 'Copy'"
              data-testid="alerts-copy"
              @click="copyManageUrl"
            />
          </div>
        </div>

        <Message severity="warn" :closable="false">
          Save this URL now -- it is the only way to inspect or unsubscribe. We do not store any
          other identifier and cannot recover it for you.
        </Message>

        <Button
          severity="secondary"
          outlined
          icon="pi pi-plus"
          label="Create another subscription"
          data-testid="alerts-reset"
          @click="resetForm"
        />
      </section>
    </main>

    <FooterBar />
  </div>
</template>
