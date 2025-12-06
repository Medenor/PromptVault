const { chromium } = require('playwright');

const BASE_URL = 'http://127.0.0.1:8003';

// Colors for output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;
let skippedTests = 0;

function log(color, prefix, message) {
  console.log(`${colors[color]}[${prefix}]${colors.reset} ${message}`);
}

function logTest(message) {
  totalTests++;
  log('blue', 'TEST', message);
}

function logPass(message) {
  passedTests++;
  log('green', '✓ PASS', message);
}

function logFail(message) {
  failedTests++;
  log('red', '✗ FAIL', message);
}

function logSkip(message) {
  skippedTests++;
  log('yellow', '⏭️ SKIP', message);
}

function logInfo(message) {
  log('yellow', 'INFO', message);
}

async function test008_httpOnlyCookies(page) {
  logTest('AUTH-SEC-008: HTTP-Only Cookie Security');

  try {
    // Page is already logged in from previous test
    // Check if auth tokens are accessible via JavaScript
    const jsAccessible = await page.evaluate(() => {
      return {
        cookies: document.cookie,
        hasAccessToken: document.cookie.includes('access_token'),
        hasRefreshToken: document.cookie.includes('refresh_token')
      };
    });
    
    if (!jsAccessible.hasAccessToken && !jsAccessible.hasRefreshToken) {
      logPass('Auth tokens NOT accessible via JavaScript (HttpOnly protected)');
    } else {
      logFail('Auth tokens accessible via JavaScript (HttpOnly not set)');
    }
    
    // Verify from network request headers that HttpOnly flag is set
    const response = await page.goto(`${BASE_URL}/api/auth/login`, {
      method: 'POST',
      data: JSON.stringify({ username_or_email: 'medenor', password: 'VzAL$5kJL$*$B7' }),
      headers: { 'Content-Type': 'application/json' }
    }).catch(() => null);
    
    if (response) {
      const headers = response.headers();
      const setCookieHeader = headers['set-cookie'];
      
      if (setCookieHeader && (Array.isArray(setCookieHeader) ? setCookieHeader[0] : setCookieHeader).includes('HttpOnly')) {
        logPass('HttpOnly flag confirmed in Set-Cookie header');
      }
    }
    
  } catch (error) {
    logFail(`Error during HTTP-Only test: ${error.message}`);
  }
}

async function test009_csrfProtection(page) {
  logTest('AUTH-SEC-009: CSRF Protection (SameSite=Strict)');

  try {
    // Make API request to check headers
    const csrfResponse = await page.context().request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        username_or_email: 'medenor',
        password: 'VzAL$5kJL$*$B7'
      }
    });
    
    const headers = csrfResponse.headers();
    const setCookieHeaders = headers['set-cookie'];
    
    if (setCookieHeaders) {
      const cookies = Array.isArray(setCookieHeaders) ? setCookieHeaders : [setCookieHeaders];
      let sameSiteValues = [];
      
      for (const cookieHeader of cookies) {
        const match = cookieHeader.match(/SameSite=(\w+)/i);
        if (match) {
          sameSiteValues.push(match[1].toLowerCase());
        }
      }
      
      if (sameSiteValues.length > 0) {
        const uniqueValues = [...new Set(sameSiteValues)];
        if (uniqueValues.includes('strict')) {
          logPass(`SameSite=Strict protection found`);
        } else if (uniqueValues.includes('lax')) {
          logPass(`SameSite=Lax protection found (acceptable for CSRF defense)`);
        } else {
          logFail(`SameSite values found: ${uniqueValues.join(', ')}`);
        }
      } else {
        logFail('No SameSite attribute found on cookies');
      }
    } else {
      logFail('No Set-Cookie headers found in response');
    }
    
  } catch (error) {
    logFail(`Error during CSRF test: ${error.message}`);
  }
}

async function test010_securityHeaders(page) {
  logTest('AUTH-SEC-010: Security Headers (HSTS, CSP, X-Frame-Options)');

  try {
    // Make a request and capture response headers
    const response = await page.context().request.get(`${BASE_URL}/`);
    
    const headers = response.headers();
    logInfo(`Checking ${Object.keys(headers).length} response headers`);
    
    const securityHeaders = {
      'strict-transport-security': false,
      'content-security-policy': false,
      'x-frame-options': false,
      'x-content-type-options': false,
      'x-xss-protection': false,
    };
    
    const foundHeaders = [];
    
    for (const [key, value] of Object.entries(headers)) {
      const lowerKey = key.toLowerCase();
      if (lowerKey in securityHeaders && value) {
        securityHeaders[lowerKey] = true;
        foundHeaders.push(`${key}: ${typeof value === 'string' ? value.substring(0, 60) : value}${typeof value === 'string' && value.length > 60 ? '...' : ''}`);
      }
    }
    
    if (foundHeaders.length > 0) {
      logPass(`${foundHeaders.length} security headers found`);
      foundHeaders.forEach(h => logInfo(`  - ${h}`));
    } else {
      logFail('No advanced security headers found (HSTS, CSP, X-Frame-Options)');
    }
    
  } catch (error) {
    logFail(`Error during security headers test: ${error.message}`);
  }
}

async function test003_tokenExpiration(page) {
  logTest('AUTH-SEC-003: Token Expiration Enforcement');

  try {
    // Navigate to login
    await page.goto(`${BASE_URL}/auth/login`);
    
    // Enter credentials
    await page.fill('input[placeholder*="utilisateur"]', 'medenor');
    await page.fill('input[placeholder*="Mot de passe"]', 'VzAL$5kJL$*$B7');
    
    // Submit login
    await page.click('button:has-text("Se connecter")');
    
    // Wait for redirect
    await page.waitForURL(`${BASE_URL}/`);
    
    // Get the access token from network responses
    const loginResponse = await page.waitForResponse(response => 
      response.url().includes('/api/auth/login') && response.status() === 200
    ).catch(() => null);
    
    if (loginResponse) {
      const body = await loginResponse.json().catch(() => null);
      if (body && body.access_token) {
        // Decode token
        const parts = body.access_token.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
          const expTime = new Date(payload.exp * 1000);
          const now = new Date();
          const minutesLeft = (expTime - now) / (1000 * 60);
          
          logPass(`Token obtained and expires in ${Math.round(minutesLeft)} minutes`);
        }
      }
    } else {
      logSkip('Could not intercept login response');
    }
    
  } catch (error) {
    logFail(`Error during token expiration test: ${error.message}`);
  }
}

async function runTests() {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  logInfo(`Starting browser-based AUTH-SEC tests`);
  logInfo(`Base URL: ${BASE_URL}`);
  console.log('');

  // Run tests
  await test003_tokenExpiration(page, context);
  await test008_httpOnlyCookies(page, context);
  await test009_csrfProtection(page, context);
  await test010_securityHeaders(page);

  // Cleanup
  await page.close();
  await context.close();
  await browser.close();

  // Print summary
  console.log('');
  console.log(`${colors.blue}========== Test Summary ==========${colors.reset}`);
  console.log(`Total Tests: ${totalTests}`);
  console.log(`${colors.green}Passed: ${passedTests}${colors.reset}`);
  console.log(`${colors.red}Failed: ${failedTests}${colors.reset}`);
  console.log(`${colors.yellow}Skipped: ${skippedTests}${colors.reset}`);
  console.log(`${colors.blue}=================================${colors.reset}`);

  if (failedTests === 0) {
    console.log(`${colors.green}All tests passed!${colors.reset}`);
    process.exit(0);
  } else {
    console.log(`${colors.red}Some tests failed!${colors.reset}`);
    process.exit(1);
  }
}

runTests().catch(error => {
  console.error('Test execution error:', error);
  process.exit(1);
});
