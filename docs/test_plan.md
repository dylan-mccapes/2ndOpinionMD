# 2ndOpinionMD.ai - Test Plan

## Overview
This document outlines a comprehensive test plan for the 2ndOpinionMD.ai MVP. It provides step-by-step procedures for testing each feature and defines the expected criteria for successful testing.

## General Testing Requirements

### Environment Setup
- **Node.js**: v18
- **Package Manager**: Yarn
- **Browser**: Latest versions of Chrome, Firefox, Safari, and Edge
- **Devices**: Desktop (1920x1080, 1366x768), Tablet (iPad), Mobile (iPhone, Android)

### Testing Approach
Since there is no formal test suite at the MVP stage, manual testing will be the primary method. As noted in the README, "If the app builds and runs (yarn dev), treat it as a successful pass."

## Feature Testing Procedures

### 1. Environment and Setup Testing

#### 1.1 Installation Test
**Steps:**
1. Clone the repository
2. Run `nvm use 18` (or ensure Node.js v18 is active)
3. Run `yarn install`

**Expected Criteria:**
- All dependencies install without errors
- No critical warnings appear during installation

#### 1.2 Development Server Test
**Steps:**
1. Run `yarn dev`
2. Open browser to http://localhost:3000

**Expected Criteria:**
- Development server starts without errors
- Application loads in the browser without console errors
- Initial page renders correctly

#### 1.3 Code Formatting Test
**Steps:**
1. Make a minor change to a file
2. Run `yarn format`

**Expected Criteria:**
- Code is formatted according to project standards
- No formatting errors are reported

### 2. UI Component Testing

#### 2.1 Navigation Bar Testing
**Steps:**
1. Load the application
2. Verify all navigation links are visible
3. Click each navigation link
4. Test responsive behavior by resizing browser window

**Expected Criteria:**
- All links are visible and properly styled
- Clicking each link navigates to the correct section/page
- Navigation bar adapts appropriately to different screen sizes
- Active page/section is visually indicated

#### 2.2 Hero Section Testing
**Steps:**
1. Load the application
2. Verify Hero Section content and styling
3. Test Hero variant A by passing variant="A" to the component
4. Test Hero variant B by passing variant="B" to the component
5. Test responsive behavior by resizing browser window

**Expected Criteria:**
- Hero section displays correctly with proper text, images, and call-to-action
- Both variants A and B render correctly with their specific designs
- Hero section adapts appropriately to different screen sizes
- Call-to-action buttons are functional

#### 2.3 Pricing Section Testing
**Steps:**
1. Navigate to the pricing section
2. Verify all pricing tiers are displayed
3. Check that pricing information is accurate ($19.99 for Basic, $49.99 for Advanced)
4. Test any interactive elements (selection, hover effects)
5. Test responsive behavior by resizing browser window

**Expected Criteria:**
- All pricing tiers display correctly with proper styling
- Pricing information matches specifications
- Interactive elements function as expected
- Pricing section adapts appropriately to different screen sizes

#### 2.4 Testimonial Carousel Testing
**Steps:**
1. Navigate to the testimonial section
2. Verify testimonials are displayed
3. Test carousel navigation (next/previous controls)
4. Test auto-rotation if implemented
5. Test responsive behavior by resizing browser window

**Expected Criteria:**
- Testimonials display correctly with proper styling
- Carousel navigation works as expected
- Auto-rotation functions correctly if implemented
- Testimonial carousel adapts appropriately to different screen sizes

#### 2.5 FAQ Accordion Testing
**Steps:**
1. Navigate to the FAQ section
2. Verify all questions are displayed
3. Click each question to expand/collapse answers
4. Test keyboard navigation (if implemented)
5. Test responsive behavior by resizing browser window

**Expected Criteria:**
- All questions display correctly with proper styling
- Clicking expands/collapses answers smoothly
- Only one answer is expanded at a time (if that's the design)
- FAQ section adapts appropriately to different screen sizes

#### 2.6 Report Overview Testing
**Steps:**
1. Navigate to the report overview section
2. Verify all report elements are displayed
3. Check any interactive elements
4. Test responsive behavior by resizing browser window

**Expected Criteria:**
- Report overview displays correctly with proper styling
- All report elements (conditions, red flags, labs, references) are visible
- Interactive elements function as expected
- Report overview adapts appropriately to different screen sizes

#### 2.7 Condition Cards Testing
**Steps:**
1. Navigate to the condition cards section
2. Verify all condition cards are displayed
3. Test any interactive elements (hover, click)
4. Test responsive behavior by resizing browser window

**Expected Criteria:**
- Condition cards display correctly with proper styling
- All information is visible and readable
- Interactive elements function as expected
- Condition cards adapt appropriately to different screen sizes

#### 2.8 Footer Testing
**Steps:**
1. Navigate to the bottom of the page
2. Verify all footer links and information are displayed
3. Click each footer link
4. Test responsive behavior by resizing browser window

**Expected Criteria:**
- Footer displays correctly with proper styling
- All links are visible and properly styled
- Clicking each link navigates to the correct section/page
- Footer adapts appropriately to different screen sizes

### 3. Core Functionality Testing

#### 3.1 Symptom Input System Testing
**Steps:**
1. Navigate to the symptom input interface
2. Enter various combinations of symptoms
3. Test form validation (required fields, format validation)
4. Test edge cases (no symptoms, maximum number of symptoms)
5. Submit the form
6. Test responsive behavior by resizing browser window

**Expected Criteria:**
- Symptom input interface displays correctly with proper styling
- Form validation works as expected
- Error messages are clear and helpful
- Submission process works correctly
- Interface adapts appropriately to different screen sizes

#### 3.2 Report Generation Testing
**Steps:**
1. Complete and submit the symptom input form
2. Verify report generation process
3. Check the generated report for all required elements
4. Test different symptom combinations to ensure varied reports
5. Test edge cases (minimal symptoms, extensive symptoms)

**Expected Criteria:**
- Report generates without errors
- Report includes all required elements:
  - Top likely conditions
  - Red-flag symptom patterns
  - Suggested labs/imaging
  - Scientific references
  - Disclaimer & next-step recommendations
- Report content varies appropriately based on input symptoms
- PDF format is correctly structured and readable

#### 3.3 Theme Support Testing
**Steps:**
1. Load the application
2. Locate and click the theme toggle in the header/navbar
3. Verify the theme changes from light to dark or vice versa
4. Refresh the page and verify theme persistence
5. Test in different browsers to ensure consistent behavior
6. Test responsive behavior by resizing browser window

**Expected Criteria:**
- Theme toggle is visible and functional in the header/navbar
- Application correctly switches between light and dark themes
- All UI elements remain visible and functional in both themes
- Theme preference is saved in localStorage and persists between sessions
- Themes display consistently across different browsers
- Theme functionality works correctly at all screen sizes

### 4. Cross-Browser and Responsive Testing

#### 4.1 Cross-Browser Testing
**Steps:**
1. Load the application in Chrome, Firefox, Safari, and Edge
2. Verify all features function correctly in each browser
3. Check for any visual inconsistencies

**Expected Criteria:**
- Application functions consistently across all tested browsers
- No significant visual differences between browsers
- No browser-specific console errors

#### 4.2 Responsive Design Testing
**Steps:**
1. Load the application on desktop, tablet, and mobile devices (or use browser dev tools to simulate)
2. Test at various screen resolutions
3. Verify all features adapt appropriately to different screen sizes
4. Test touch interactions on touch-enabled devices

**Expected Criteria:**
- Application displays correctly at all tested screen sizes
- No horizontal scrolling on mobile devices
- Touch interactions work correctly on touch-enabled devices
- All features remain accessible and usable at all screen sizes

### 5. Performance Testing

#### 5.1 Load Time Testing
**Steps:**
1. Use browser dev tools to measure page load time
2. Test initial load and subsequent navigation
3. Test with cache cleared and with cached resources

**Expected Criteria:**
- Initial page load completes in under 3 seconds on broadband connection
- Subsequent navigation is responsive (under 1 second)
- Application performs acceptably even on slower connections

#### 5.2 Resource Usage Testing
**Steps:**
1. Use browser dev tools to monitor memory and CPU usage
2. Test during normal usage and during intensive operations
3. Test for memory leaks during extended usage

**Expected Criteria:**
- Memory usage remains stable during normal operation
- CPU usage spikes only during expected intensive operations
- No significant memory leaks during extended usage

### 6. Accessibility Testing

#### 6.1 Basic Accessibility Testing
**Steps:**
1. Test keyboard navigation throughout the application
2. Verify proper heading structure
3. Check for sufficient color contrast in both themes
4. Verify all images have alt text
5. Test with screen reader if available

**Expected Criteria:**
- All interactive elements are keyboard accessible
- Heading structure follows a logical hierarchy
- Color contrast meets WCAG AA standards
- All images have descriptive alt text
- Screen reader can navigate and interpret the application correctly

## Test Reporting

After completing each test, record the results in the test report document, including:
- Test date and tester name
- Test environment details
- Pass/fail status for each test
- Description of any issues found
- Screenshots of issues (if applicable)
- Recommendations for fixes
