

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting 2ndOpinionMD Express Server Tests${NC}"

echo -e "\n${YELLOW}Checking MongoDB status...${NC}"
if systemctl is-active --quiet mongod; then
  echo -e "${GREEN}MongoDB is running${NC}"
else
  echo -e "${RED}MongoDB is not running. Starting MongoDB...${NC}"
  sudo systemctl start mongod
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}MongoDB started successfully${NC}"
  else
    echo -e "${RED}Failed to start MongoDB. Please check MongoDB installation.${NC}"
    exit 1
  fi
fi

echo -e "\n${YELLOW}Checking if server is running...${NC}"
if curl -s http://localhost:3000 > /dev/null; then
  echo -e "${GREEN}Server is running${NC}"
else
  echo -e "${RED}Server is not running. Please start the server with 'npm run dev' in another terminal.${NC}"
  exit 1
fi

TEMP_DIR=$(mktemp -d)
echo -e "\n${YELLOW}Creating temporary directory for test results: ${TEMP_DIR}${NC}"

echo -e "\n${YELLOW}Testing user registration...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:3000/api/auth/register -H "Content-Type: application/json" -d '{"email":"testuser@example.com","password":"password123","firstName":"Test","lastName":"User"}')
echo $REGISTER_RESPONSE > $TEMP_DIR/register.json

if echo $REGISTER_RESPONSE | grep -q '"success":true'; then
  echo -e "${GREEN}User registration successful${NC}"
  TOKEN=$(echo $REGISTER_RESPONSE | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
  echo "TOKEN=$TOKEN" > $TEMP_DIR/token.txt
else
  echo -e "${RED}User registration failed${NC}"
  echo $REGISTER_RESPONSE
fi

echo -e "\n${YELLOW}Testing user login...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:3000/api/auth/login -H "Content-Type: application/json" -d '{"email":"testuser@example.com","password":"password123"}')
echo $LOGIN_RESPONSE > $TEMP_DIR/login.json

if echo $LOGIN_RESPONSE | grep -q '"success":true'; then
  echo -e "${GREEN}User login successful${NC}"
  TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
  echo "TOKEN=$TOKEN" > $TEMP_DIR/token.txt
else
  echo -e "${RED}User login failed${NC}"
  echo $LOGIN_RESPONSE
fi

source $TEMP_DIR/token.txt

echo -e "\n${YELLOW}Testing user profile...${NC}"
PROFILE_RESPONSE=$(curl -s -X GET http://localhost:3000/api/user/profile -H "Authorization: Bearer $TOKEN")
echo $PROFILE_RESPONSE > $TEMP_DIR/profile.json

if echo $PROFILE_RESPONSE | grep -q '"success":true'; then
  echo -e "${GREEN}User profile retrieval successful${NC}"
else
  echo -e "${RED}User profile retrieval failed${NC}"
  echo $PROFILE_RESPONSE
fi

echo -e "\n${YELLOW}Testing diagnosis...${NC}"
DIAGNOSE_RESPONSE=$(curl -s -X POST http://localhost:3000/api/diagnose -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"age":"35","sex":"female","symptoms":["fatigue","joint_pain","rash"],"durationMonths":"6"}')
echo $DIAGNOSE_RESPONSE > $TEMP_DIR/diagnose.json

if echo $DIAGNOSE_RESPONSE | grep -q '"success":true'; then
  echo -e "${GREEN}Diagnosis successful${NC}"
  REPORT_ID=$(echo $DIAGNOSE_RESPONSE | grep -o '"reportId":"[^"]*"' | cut -d'"' -f4)
  echo "REPORT_ID=$REPORT_ID" > $TEMP_DIR/report_id.txt
else
  echo -e "${RED}Diagnosis failed${NC}"
  echo $DIAGNOSE_RESPONSE
fi

source $TEMP_DIR/report_id.txt

echo -e "\n${YELLOW}Testing PDF generation...${NC}"
PDF_RESPONSE=$(curl -s -X POST http://localhost:3000/api/generate-pdf -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "{\"reportId\":\"$REPORT_ID\"}")
echo $PDF_RESPONSE | head -c 1000 > $TEMP_DIR/pdf.json

if echo $PDF_RESPONSE | grep -q '"success":true'; then
  echo -e "${GREEN}PDF generation successful${NC}"
else
  echo -e "${RED}PDF generation failed${NC}"
  echo $PDF_RESPONSE | head -c 1000
fi

echo -e "\n${YELLOW}Testing reports retrieval...${NC}"
REPORTS_RESPONSE=$(curl -s -X GET http://localhost:3000/api/reports -H "Authorization: Bearer $TOKEN")
echo $REPORTS_RESPONSE > $TEMP_DIR/reports.json

if echo $REPORTS_RESPONSE | grep -q '"success":true'; then
  echo -e "${GREEN}Reports retrieval successful${NC}"
else
  echo -e "${RED}Reports retrieval failed${NC}"
  echo $REPORTS_RESPONSE
fi

echo -e "\n${YELLOW}Testing form fields retrieval...${NC}"

SYMPTOMS_RESPONSE=$(curl -s -X GET http://localhost:3000/api/fields/symptoms -H "Authorization: Bearer $TOKEN")
echo $SYMPTOMS_RESPONSE > $TEMP_DIR/symptoms.json

if echo $SYMPTOMS_RESPONSE | grep -q '"success":true'; then
  echo -e "${GREEN}Symptoms retrieval successful${NC}"
else
  echo -e "${RED}Symptoms retrieval failed${NC}"
  echo $SYMPTOMS_RESPONSE
fi

PRIOR_DIAGNOSES_RESPONSE=$(curl -s -X GET http://localhost:3000/api/fields/prior-diagnoses -H "Authorization: Bearer $TOKEN")
echo $PRIOR_DIAGNOSES_RESPONSE > $TEMP_DIR/prior_diagnoses.json

if echo $PRIOR_DIAGNOSES_RESPONSE | grep -q '"success":true'; then
  echo -e "${GREEN}Prior diagnoses retrieval successful${NC}"
else
  echo -e "${RED}Prior diagnoses retrieval failed${NC}"
  echo $PRIOR_DIAGNOSES_RESPONSE
fi

SEX_OPTIONS_RESPONSE=$(curl -s -X GET http://localhost:3000/api/fields/sex-options -H "Authorization: Bearer $TOKEN")
echo $SEX_OPTIONS_RESPONSE > $TEMP_DIR/sex_options.json

if echo $SEX_OPTIONS_RESPONSE | grep -q '"success":true'; then
  echo -e "${GREEN}Sex options retrieval successful${NC}"
else
  echo -e "${RED}Sex options retrieval failed${NC}"
  echo $SEX_OPTIONS_RESPONSE
fi

echo -e "\n${YELLOW}Testing invalid token...${NC}"
INVALID_TOKEN_RESPONSE=$(curl -s -X GET http://localhost:3000/api/user/profile -H "Authorization: Bearer invalid_token")
echo $INVALID_TOKEN_RESPONSE > $TEMP_DIR/invalid_token.json

if echo $INVALID_TOKEN_RESPONSE | grep -q '"error":"Forbidden"'; then
  echo -e "${GREEN}Invalid token test successful${NC}"
else
  echo -e "${RED}Invalid token test failed${NC}"
  echo $INVALID_TOKEN_RESPONSE
fi

echo -e "\n${YELLOW}Testing missing token...${NC}"
MISSING_TOKEN_RESPONSE=$(curl -s -X GET http://localhost:3000/api/user/profile)
echo $MISSING_TOKEN_RESPONSE > $TEMP_DIR/missing_token.json

if echo $MISSING_TOKEN_RESPONSE | grep -q '"error":"Unauthorized"'; then
  echo -e "${GREEN}Missing token test successful${NC}"
else
  echo -e "${RED}Missing token test failed${NC}"
  echo $MISSING_TOKEN_RESPONSE
fi

echo -e "\n${YELLOW}Testing invalid report ID...${NC}"
INVALID_REPORT_RESPONSE=$(curl -s -X POST http://localhost:3000/api/generate-pdf -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"reportId":"invalid_id"}')
echo $INVALID_REPORT_RESPONSE > $TEMP_DIR/invalid_report.json

if echo $INVALID_REPORT_RESPONSE | grep -q '"error":"'; then
  echo -e "${GREEN}Invalid report ID test successful${NC}"
else
  echo -e "${RED}Invalid report ID test failed${NC}"
  echo $INVALID_REPORT_RESPONSE
fi

echo -e "\n${YELLOW}Test Results Summary${NC}"
echo -e "Test results saved in: ${TEMP_DIR}"
echo -e "User registration: $(if grep -q '"success":true' $TEMP_DIR/register.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "User login: $(if grep -q '"success":true' $TEMP_DIR/login.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "User profile: $(if grep -q '"success":true' $TEMP_DIR/profile.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "Diagnosis: $(if grep -q '"success":true' $TEMP_DIR/diagnose.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "PDF generation: $(if grep -q '"success":true' $TEMP_DIR/pdf.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "Reports retrieval: $(if grep -q '"success":true' $TEMP_DIR/reports.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "Symptoms retrieval: $(if grep -q '"success":true' $TEMP_DIR/symptoms.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "Prior diagnoses retrieval: $(if grep -q '"success":true' $TEMP_DIR/prior_diagnoses.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "Sex options retrieval: $(if grep -q '"success":true' $TEMP_DIR/sex_options.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "Invalid token test: $(if grep -q '"error":"Forbidden"' $TEMP_DIR/invalid_token.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "Missing token test: $(if grep -q '"error":"Unauthorized"' $TEMP_DIR/missing_token.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "Invalid report ID test: $(if grep -q '"error":"' $TEMP_DIR/invalid_report.json; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"

echo -e "\n${YELLOW}Tests completed${NC}"
