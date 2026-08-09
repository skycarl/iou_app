/**
 * The only public route besides /healthcheck. The random segment keeps the
 * endpoint from being discoverable; the secret-token header is what actually
 * authenticates a request. Changing this requires re-running setWebhook.
 */
export const WEBHOOK_PATH = '/telegram/494e082e23b910f6e23630bf9626faf1';
