# Manual Visual Testing Checklist - Phase 5

**Time Required**: ~30 minutes
**Servers Required**: Backend (8003) and Frontend (5174) running
**Login**: login / password

---

## ✅ QUICK START CHECKLIST

### 1. LOGIN PAGE (5 min)

Navigate to: <http://localhost:8003/>

**Visual Checks:**

- [X] ~~*Page loads (no errors in console)*~~ [2025-12-22]
- [X] ~~*Blue header visible*~~ [2025-12-22]
- [X] ~~*PromptVault logo visible*~~ [2025-12-22]
- [X] ~~*Login form properly styled*~~ [2025-12-22]
- [X] ~~*Email input has gray border*~~ [2025-12-22]
- [X] ~~*Password input has gray border*~~ [2025-12-22]
- [X] ~~*Login button is blue and prominent*~~ [2025-12-22]
- [X] ~~*"Forgot password?" link visible*~~ [2025-12-22]
- [X] ~~*"Don't have account? Register" link visible*~~ [2025-12-22]
- [X] ~~*Language selector visible*~~ [2025-12-22]

**Functional Check:**

- [X] ~~*Enter: your login*~~ [2025-12-22]
- [X] ~~*Password: your password*~~ [2025-12-22]
- [X] ~~*Click Login → redirects to main app (no console errors)*~~ [2025-12-22]

---

### 2. MAIN APP PAGE (8 min)

You should now be at: <http://localhost:8003/>

**Visual Checks:**

- [X] ~~*Blue header with logo*~~ [2025-12-22]
- [X] ~~*"Create New Prompt" button visible (blue, prominent)*~~ [2025-12-22]
- [X] ~~*Search bar visible at top*~~ [2025-12-22]
- [X] ~~*Category filter visible*~~ [2025-12-22]
- [X] ~~*Tag filter visible*~~ [2025-12-22]
- [X] ~~*Prompt cards visible in grid*~~ [2025-12-22]
- [X] ~~*Each card shows: Title, description, tags (as badges), category, date*~~ [2025-12-22]
- [X] ~~*Edit/Delete/Versions buttons visible on each card*~~ [2025-12-22]
- [X] ~~*Hover on card → scales slightly*~~ [2025-12-22]
- [X] ~~*Hover on button → scales up*~~ [2025-12-22]

**Functional Checks:**

- [X] ~~*Click "Create New Prompt" → modal opens*~~ [2025-12-22]
- [X] ~~*Modal has form fields visible*~~ [2025-12-22]
- [X] ~~*Modal has Save/Cancel buttons*~~ [2025-12-22]
- [X] ~~*Close modal (click X or Cancel)*~~ [2025-12-22]
- [X] ~~*Type in search box → results filter in real-time*~~ [2025-12-22]
- [X] ~~*Select category from dropdown → filters results*~~ [2025-12-22]
- [X] ~~*Click Edit on a prompt → modal opens with data*~~ [2025-12-22]
- [X] ~~*Click Delete on a prompt → gets removed*~~ [2025-12-22]

**Responsive Check (F12 DevTools):**

- [X] ~~*Resize to 375px width → grid becomes 1 column*~~ [2025-12-22]
- [X] ~~*Resize to 768px width → grid becomes 2 columns*~~ [2025-12-22]
- [X] ~~*Resize to 1440px width → grid becomes 3 columns*~~ [2025-12-22]

---

### 3. USER PROFILE PAGE (5 min)

Click your username in header → Profile

**Visual Checks:**

- [X] ~~*Blue header*~~ [2025-12-22]
- [X] ~~*"Profile Information" card visible*~~ [2025-12-22]
- [X] ~~*Username field (readonly, grayed out)*~~ [2025-12-22]
- [X] ~~*Email field visible*~~ [2025-12-22]
- [X] ~~*"Preferences" card visible*~~ [2025-12-22]
- [X] ~~*Language selector visible*~~ [2025-12-22]
- [X] ~~*"Security" card visible*~~ [2025-12-22]
- [X] ~~*Password change form visible*~~ [2025-12-22]
- [X] ~~*Password strength indicator visible*~~ [2025-12-22]

**Functional Checks:**

- [X] ~~*Select different language → dropdown works*~~ [2025-12-22]
- [X] ~~*Click password change → form expands/shows*~~ [2025-12-22]
- [X] ~~*Type password → strength indicator updates (color changes)*~~ [2025-12-22]
- [X] ~~*No errors on page*~~ [2025-12-22]

---

### 4. ADMIN USERS PAGE (5 min)

Click on admin menu or navigate to: <http://localhost:8003/admin/users>

**Visual Checks:**

- [X] ~~*Blue header with navigation*~~ [2025-12-22]
- [X] ~~*Search filter visible*~~ [2025-12-22]
- [X] ~~*Role filter dropdown visible*~~ [2025-12-22]
- [X] ~~*Status filter dropdown visible*~~ [2025-12-22]
- [X] ~~*User list/table visible*~~ [2025-12-22]
- [X] ~~*Each user shows: username, email, role (badge), status (badge)*~~ [2025-12-22]
- [X] ~~*Role badges color-coded (admin=red, user=blue)*~~ [2025-12-22]
- [X] ~~*Status badges color-coded (active=green, inactive=gray)*~~ [2025-12-22]
- [X] ~~*Edit/Delete buttons visible for each user*~~ [2025-12-22]

**Functional Checks:**

- [X] ~~*Type in search → filters users*~~ [2025-12-22]
- [X] ~~*Select role from dropdown → filters results*~~ [2025-12-22]
- [X] ~~*Click Edit on a user → modal opens*~~ [2025-12-22]
- [X] ~~*Modal closes properly*~~ [2025-12-22]

---

### 5. ADMIN SESSIONS PAGE (3 min)

Navigate to: <http://localhost:8003/admin/sessions>

**Visual Checks:**

- [X] ~~*Blue header*~~ [2025-12-22]
- [X] ~~*Sessions table visible*~~ [2025-12-22]
- [X] ~~*Each session shows: user, IP, browser, login time*~~ [2025-12-22]
- [X] ~~*"Terminate" button visible for each session (red)*~~ [2025-12-22]
- [X] ~~*Current session highlighted differently*~~ [2025-12-22]

**Functional Checks:**

- [X] ~~*Page loads without errors*~~ [2025-12-22]
- [X] ~~*Table displays properly*~~ [2025-12-22]

---

### 6. IMPORT/EXPORT PAGE (2 min)

Navigate to: <http://localhost:8003/import-export>

**Visual Checks:**

- [X] ~~*Two-section layout visible (Export left, Import right)*~~ [2025-12-22]
- [X] ~~*Export section: format selector, options, Export button*~~ [2025-12-22]
- [X] ~~*Import section: upload area, format selector, Import button*~~ [2025-12-22]
- [X] ~~*Both sections clearly separated*~~ [2025-12-22]
- [X] ~~*Buttons properly styled (blue for primary)*~~ [2025-12-22]

**Functional Checks:**

- [X] ~~*Page loads without errors*~~ [2025-12-22]
- [X] ~~*No broken layout*~~ [2025-12-22]

---

### 7. BACKUP MANAGEMENT PAGE (2 min)

Navigate to: <http://localhost:8003/backup>

**Visual Checks:**

- [X] ~~*Blue header*~~ [2025-12-22]
- [X] ~~*"Create Backup" button visible (blue)*~~ [2025-12-22]
- [X] ~~*Backup list/cards visible*~~ [2025-12-22]
- [X] ~~*Each backup shows: filename, size, date, actions*~~ [2025-12-22]
- [X] ~~*Download/Delete buttons visible for each backup*~~ [2025-12-22]
- [X] ~~*Cleanup and other action buttons visible*~~ [2025-12-22]

**Functional Checks:**

- [X] ~~*Page loads without errors*~~ [2025-12-22]
- [X] ~~*Backups display properly*~~ [2025-12-22]

---

## 📋 OVERALL CHECKS

### Console Errors (F12 > Console)

- [X] ~~*NO red error messages*~~ [2025-12-22]
- [X] ~~*NO warnings about missing CSS or fonts*~~ [2025-12-22]
- [X] ~~*NO 404 errors*~~ [2025-12-22]

### Network Tab (F12 > Network)

- [X] ~~*Outfit font loads successfully*~~ [2025-12-22]
- [X] ~~*CSS bundle loads (look for `tailwind-globals.*.css`)*~~ [2025-12-22]
- [X] ~~*All JS bundles load*~~ [2025-12-22]
- [X] ~~*No failed requests (all 200 status)*~~ [2025-12-22]

### Design Consistency

- [X] ~~*All headers are blue (#3B82F6 or similar)*~~ [2025-12-22]
- [X] ~~*All cards have borders (gray #E5E7EB)*~~ [2025-12-22]
- [X] ~~*All inputs have gray border (#E5E7EB) normally, blue on focus*~~ [2025-12-22]
- [X] ~~*No shadows anywhere (flat design ✓)*~~ [2025-12-22]
- [X] ~~*All text uses Outfit font (check in DevTools)*~~ [2025-12-22]
- [X] ~~*Spacing looks consistent*~~ [2025-12-22]
- [X] ~~*Colors match spec (Blue, Red, Green, Amber, Gray)*~~ [2025-12-22]

### Accessibility Check

- [X] ~~*Press Tab → focus moves through elements*~~ [2025-12-22]
- [X] ~~*Focus ring is visible (blue outline)*~~ [2025-12-22]
- [X] ~~*Can Tab into form inputs*~~ [2025-12-22]
- [X] ~~*Can submit forms with Enter key*~~ [2025-12-22]
- [X] ~~*Open modal, press ESC → modal closes*~~ [2025-12-22]

---

## 🎯 FINAL DECISION

After completing these checks, answer:

### All Checks Passed? ✅ YES / ❌ NO

If **YES → PROCEED TO PHASE 6** (Code Cleanup & Documentation)

If **NO → List Issues Below**:

```
Issue 1: [describe]
Issue 2: [describe]
```

---

## ⏱️ TESTING TIMELINE

- Pages 1-3: 5 + 8 + 5 = 18 minutes
- Pages 4-7: 5 + 3 + 2 + 2 = 12 minutes
- **Total: ~30 minutes**

**Start Time**: [Your time]
**Expected End Time**: [Your time + 30 min]

---

## 📸 QUICK SCREENSHOTS (Optional)

If you want to document the redesign, take screenshots of:

1. Login page
2. Main app page (desktop, full width)
3. Main app page (mobile, 375px)
4. Admin page
5. User profile page

Good luck! 🚀
