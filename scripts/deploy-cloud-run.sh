#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT first}"
REGION="${GOOGLE_CLOUD_RUN_REGION:-us-central1}"
MODEL_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"
SERVICE="${FLOWBOUND_SERVICE:-flowbound}"
TOPIC="${FLOWBOUND_PUBSUB_TOPIC:-flowbound-events}"
SA_NAME="${FLOWBOUND_SERVICE_ACCOUNT:-flowbound-runtime}"
SA="${SA_NAME}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"

gcloud config set project "$GOOGLE_CLOUD_PROJECT"
gcloud services enable run.googleapis.com aiplatform.googleapis.com firestore.googleapis.com pubsub.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

gcloud pubsub topics describe "$TOPIC" >/dev/null 2>&1 || gcloud pubsub topics create "$TOPIC"
gcloud iam service-accounts describe "$SA" >/dev/null 2>&1 || gcloud iam service-accounts create "$SA_NAME" --display-name="FlowBound runtime"

for role in roles/datastore.user roles/pubsub.publisher roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" --member="serviceAccount:$SA" --role="$role" --quiet >/dev/null
done

# Firestore Native database must already exist. Do not create/delete stateful resources implicitly.
gcloud firestore databases describe --database='(default)' >/dev/null

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --service-account "$SA" \
  --allow-unauthenticated \
  --set-env-vars "FLOWBOUND_BACKEND=cloud,FLOWBOUND_AGENT_MODE=google,FLOWBOUND_PUBSUB_TOPIC=$TOPIC,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$MODEL_LOCATION,GOOGLE_GENAI_USE_VERTEXAI=TRUE"

gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)'
