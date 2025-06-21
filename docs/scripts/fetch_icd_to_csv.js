// icd_api_to_csv.js
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const createCsvWriter = require("csv-writer").createObjectCsvWriter;

// === CONFIGURATION ===
const CLIENT_ID = "0889cf5f-c905-44d8-8f05-d6b8932cccb6_b25c0c01-e2ed-4f28-88f9-3327cdfb4fc5";
const CLIENT_SECRET = "KploZIGagCKib7G6wUGnqaYYzxFRlq|UFvQGcTYP84E=";
const TOKEN_URL = "https://id.who.int/token"; // Replace with real WHO token URL
const API_URL = "https://id.who.int/icd/entity?linearization=foundation"; // Replace with actual ICD API URL

// Save to your GitHub repo's /docs directory
const OUTPUT_DIR = "./docs";
const OUTPUT_FILE = "icd_output.csv";

const csvWriter = createCsvWriter({
  path: path.join(OUTPUT_DIR, OUTPUT_FILE),
  header: [
    { id: "id", title: "ID" },
    { id: "title", title: "Title" },
    { id: "code", title: "ICD Code" },
    { id: "definition", title: "Definition" },
  ],
});

async function fetchAccessToken() {
  try {
    const formParams = new URLSearchParams();
    formParams.append("grant_type", "client_credentials");
    formParams.append("client_id", CLIENT_ID);
    formParams.append("client_secret", CLIENT_SECRET);

    const response = await axios.post(TOKEN_URL, formParams, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    return response.data.access_token;
  } catch (error) {
    throw new Error(`Token request failed: ${error.response?.data?.error_description || error.message}`);
  }
}

async function fetchICDData(accessToken) {
  try {
    const response = await axios.get(API_URL, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Accept: "application/json",
      },
    });

    return response.data;
  } catch (error) {
    throw new Error(`API request failed: ${error.response?.status} ${error.message}`);
  }
}

async function saveToCSV(records) {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  await csvWriter.writeRecords(records);
  console.log(`✅ CSV saved to ${path.join(OUTPUT_DIR, OUTPUT_FILE)}`);
}

async function main() {
  try {
    console.log("🔐 Requesting access token...");
    const token = await fetchAccessToken();

    console.log("📡 Fetching ICD data...");
    const data = await fetchICDData(token);

    const formatted = (data?.child || []).map((item) => ({
      id: item.id || "N/A",
      title: item.title?.["@value"] || "N/A",
      code: item.theCode || "N/A",
      definition: item.definition?.["@value"] || "N/A",
    }));

    if (!formatted.length) {
      console.warn("⚠️ No records found to save.");
    } else {
      await saveToCSV(formatted);
    }
  } catch (err) {
    console.error("❌ Error:", err.message);
  }
}

main();
