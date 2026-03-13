import pandas as pd
from openai import OpenAI
import random
from tqdm import tqdm
import time

# =============================
# DeepSeek API
# =============================
client = OpenAI(
    api_key="YOUR-API",
    base_url="https://api.deepseek.com"
)

# =============================
# Load dataset
# =============================
df = pd.read_csv("test_data.csv")

# =============================
# Sample tối đa 20 dòng mỗi subcategory
# =============================
df_sample = (
    df.groupby("subcategory", group_keys=False)
      .apply(lambda x: x.sample(min(len(x), 20), random_state=42))
      .reset_index(drop=True)
)

print("Rows after sampling:", len(df_sample))


# =============================
# Generate claim
# =============================
def generate_claim(title, description, label):

    prompt = f"""
You are generating claims for a fact-checking dataset.

Title: {title}
Description: {description}

Task:
Create ONE claim containing 1–3 subclaims.

Rules:
- If label = true → claim must be correct.
- If label = false → change some details (time, location, person, number).
- Make the claim natural like a news statement.
- Output ONLY the claim text.

Label: {label}
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You generate claims for fact checking datasets."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()


claims = []
labels = []

for _, row in tqdm(df_sample.iterrows(), total=len(df_sample)):

    title = row["title"]
    desc = row["description"]

    # đảm bảo 60/40
    label = "true" if random.random() < 0.6 else "false"

    try:
        claim = generate_claim(title, desc, label)
    except Exception as e:
        print("API error:", e)
        claim = ""

    claims.append(claim)
    labels.append(label)

    time.sleep(0.5)


# =============================
# Chỉ giữ 3 cột
# =============================
result = pd.DataFrame({
    "id": df_sample["id"],
    "claim": claims,
    "label": labels
})

# =============================
# Save file
# =============================
result.to_csv("fact_check_claims.csv", index=False)

print("Saved file: fact_check_claims.csv")