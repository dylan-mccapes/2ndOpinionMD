# 2ndOpinionMD.ai – Test Plan

This document outlines the testing strategy for the 2ndOpinionMD.ai MVP, focusing on the authentication system, journaling feature, and OpenAI integration.

## 🧪 Testing Approach

Since we don't have a formal test suite at the MVP stage, this document provides manual testing procedures to verify functionality before deployment.

## 🔒 Authentication Testing

### User Registration
1. Navigate to `/splash` or `/register`
2. Fill out the registration form with:
   - Full name
   - Email address
   - Password (with confirmation)
3. Submit the form
4. Verify:
   - Success message appears
   - User is redirected to the dashboard
   - MongoDB contains the new user record with hashed password

### User Login
1. Navigate to `/splash` or `/login`
2. Enter registered email and password
3. Submit the form
4. Verify:
   - User is authenticated and redirected to the dashboard
   - JWT token is stored in localStorage
   - User information is stored in localStorage

### Authentication Protection
1. Clear localStorage (logout)
2. Attempt to access protected routes directly:
   - `/dashboard`
   - `/journal`
   - `/journal/new`
3. Verify:
   - User is redirected to the login page
   - Protected content is not visible

### Logout Functionality
1. Login to the application
2. Click the logout button in the navigation
3. Verify:
   - User is logged out
   - localStorage is cleared of tokens and user data
   - User is redirected to the splash page

## 📝 Journaling Feature Testing

### Journal Entry Creation
1. Login to the application
2. Navigate to `/journal/new`
3. Create a new journal entry with:
   - Multiple symptoms with severity ratings
   - Environmental factors
   - Stress level
   - Sleep quality
   - Diet notes
4. Submit the form
5. Verify:
   - Entry is saved to MongoDB
   - User is redirected to the journal list with success message
   - Entry appears in the journal list

### Journal List View
1. Login to the application
2. Navigate to `/journal`
3. Verify:
   - All user journal entries are displayed
   - Entries show date, symptom preview, and severity indicators
   - Entries are sorted by date (newest first)

### Journal Detail View
1. Login to the application
2. Navigate to `/journal`
3. Click on a journal entry
4. Verify:
   - Full entry details are displayed
   - Symptoms with severity are shown
   - Environmental factors are listed
   - AI analysis is displayed
   - Follow-up questions are shown

### Journal Entry Deletion
1. Login to the application
2. Navigate to `/journal`
3. Click the delete button on an entry
4. Confirm deletion
5. Verify:
   - Entry is removed from the list
   - Entry is deleted from MongoDB

## 🧠 OpenAI Integration Testing

### AI Analysis Generation
1. Login to the application
2. Create a new journal entry
3. Submit the form
4. Verify:
   - AI analysis is generated
   - Analysis includes potential diagnoses
   - Analysis includes follow-up questions
   - Analysis references symptoms and factors from the entry

### Historical Context Integration
1. Login to the application
2. Create multiple journal entries over time
3. Verify:
   - Later AI analyses reference earlier entries
   - Follow-up questions evolve based on previous responses
   - Patterns across entries are identified

### Symptom Tracking from Intake
1. Complete the symptom intake form with demographics
2. Login and navigate to the journal
3. Verify:
   - Initial symptoms from intake are recorded with correct dates
   - Demographics are associated with the user profile
   - Initial symptoms appear in AI analysis context

## 🔄 Integration Testing

### Frontend-Backend Communication
1. Monitor network requests during:
   - Authentication
   - Journal entry creation
   - Journal entry retrieval
2. Verify:
   - Proper API endpoints are called
   - Authentication headers are included
   - Response data is correctly formatted
   - Error handling works as expected

### MongoDB Integration
1. Perform various operations in the application
2. Check MongoDB collections:
   - users
   - journal_entries
3. Verify:
   - Data is correctly stored
   - Relationships between collections are maintained
   - Queries return expected results

### OpenAI API Integration
1. Create journal entries
2. Monitor OpenAI API requests
3. Verify:
   - Correct model is used
   - Prompts include all necessary context
   - Responses are properly parsed and stored

## 🚨 Error Handling Testing

### Form Validation
1. Submit forms with invalid data:
   - Empty required fields
   - Invalid email format
   - Password mismatch
2. Verify:
   - Appropriate error messages are displayed
   - Form is not submitted
   - User can correct errors and resubmit

### API Error Handling
1. Simulate API errors:
   - Disconnect from MongoDB
   - Invalid OpenAI API key
2. Verify:
   - User-friendly error messages are displayed
   - Application doesn't crash
   - Retry mechanisms work as expected

### Authentication Failures
1. Attempt login with:
   - Non-existent user
   - Incorrect password
   - Expired token
2. Verify:
   - Appropriate error messages are displayed
   - Security is not compromised

## 📱 Responsive Design Testing

### Device Testing
Test the application on:
1. Desktop (various screen sizes)
2. Tablet (portrait and landscape)
3. Mobile (portrait and landscape)

### Functionality Verification
Verify on each device:
1. All features work correctly
2. UI elements are properly sized and positioned
3. Forms are usable and accessible
4. Journal entries are readable

## 🔐 Security Testing

### Authentication Security
1. Verify passwords are properly hashed in the database
2. Check for secure JWT implementation
3. Test token expiration and renewal
4. Verify protected routes are properly secured

### Data Protection
1. Verify sensitive data is not exposed in:
   - API responses
   - Local storage
   - Console logs
2. Check that user data is isolated (users can't access others' data)

## 🚀 Deployment Testing

### Environment Configuration
1. Verify all environment variables are properly set
2. Test with production API keys
3. Ensure MongoDB connection works in production environment

### Build Process
1. Run production build
2. Verify assets are properly bundled and minified
3. Check for any build warnings or errors

## 📋 Test Reporting

Document any issues found during testing:
1. Issue description
2. Steps to reproduce
3. Expected vs. actual behavior
4. Screenshots or logs
5. Severity level

## 🔄 Regression Testing

After fixing issues:
1. Retest the affected functionality
2. Verify the fix doesn't break other features
3. Run through critical user flows again

## 📊 Performance Testing

### Load Time
1. Measure initial load time
2. Measure time to interactive
3. Verify performance on slower connections

### API Response Time
1. Measure response time for:
   - Authentication requests
   - Journal entry creation
   - Journal entry retrieval
   - OpenAI API integration

## 🔍 Accessibility Testing

1. Test keyboard navigation
2. Verify screen reader compatibility
3. Check color contrast
4. Ensure form elements have proper labels

## 📝 Test Execution Checklist

Use this checklist before submitting the PR:

- [ ] Authentication flows tested and working
- [ ] Journal creation, viewing, and deletion tested
- [ ] OpenAI integration verified with proper responses
- [ ] Historical context in journal entries confirmed
- [ ] Symptom tracking from intake page verified
- [ ] Responsive design checked on multiple devices
- [ ] Error handling tested for common scenarios
- [ ] Security measures verified
- [ ] Performance acceptable on target devices
