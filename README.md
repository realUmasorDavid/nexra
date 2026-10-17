# Paystack payments

Set `PAYSTACK_SECRET_KEY` in the server environment. In the Paystack dashboard,
configure the webhook URL as `https://<your-domain>/orders/payment/webhook/`
and enable the `charge.success` event.

The callback verifies transactions with Paystack, and the webhook verifies
Paystack's HMAC signature. Both paths validate the transaction reference,
amount, and NGN currency before marking an order paid. Stock is checked during
checkout without being reserved, then deducted once when payment succeeds.
If payment succeeds after the ordered quantity is no longer available, the
order is marked paid but remains pending for manual review; this is logged.

# Supabase Storage

The app can use Supabase Storage's S3-compatible API for uploaded media and
collected static files. Create two **public** buckets in Supabase Storage,
`nexra-media` and `nexra-static` (or set different bucket names below). Public
buckets allow anyone with an asset URL to read those files. Keep uploads that
must be private in a separate private bucket.

In Supabase project settings, generate S3 access keys and copy the S3 endpoint
and region from the Storage S3 configuration page. Set these server environment
variables:

```text
SUPABASE_STORAGE_ENABLED=true
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_S3_ENDPOINT_URL=https://<project-ref>.storage.supabase.co/storage/v1/s3
SUPABASE_S3_REGION=<region-from-supabase-s3-settings>
SUPABASE_S3_ACCESS_KEY_ID=<generated-s3-access-key-id>
SUPABASE_S3_SECRET_ACCESS_KEY=<generated-s3-secret-access-key>
SUPABASE_STATIC_BUCKET=nexra-static
SUPABASE_MEDIA_BUCKET=nexra-media
```

Use the generated S3 credentials, not a Supabase `service_role` or anon key.
The S3 credentials grant server-side storage access; do not expose them in
frontend code or commit them to the repository. When Supabase storage is
disabled, Django uses its normal local file storage.

After deploying the settings and credentials, upload the existing local media
files to the media bucket and run:

```sh
python manage.py collectstatic
```

`collectstatic` uploads static assets to the static bucket. Both buckets must
be public for the generated asset URLs to work.
