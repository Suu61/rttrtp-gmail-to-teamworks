import { test, expect } from '@playwright/test';
import { defineConfig } from '@playwright/test';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';

const today = new Date().toISOString().split('T')[0];
const logDir = path.join('logs', today);

fs.mkdirSync(logDir, { recursive: true });

dotenv.config();

export default defineConfig({
  use: {
    baseURL: process.env.BASE_URL
  },
  outputDir: `${logDir}/test-results`,
  reporter: [
    ['list'],
    ['html']
  ]
})

const username = process.env.USER_NAME
const password = process.env.PASS_WORD

test('test', async ({ page }) => {
  await page.goto('https://sportsync.smartabase.com/ssi/auth');
  await page.getByRole('button', { name: 'Close this dialog' }).click();
  await page.getByTestId('username').click();
  await page.getByTestId('username').fill(username);
  await page.getByTestId('password').click();
  await page.getByTestId('password').fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.goto('https://sportsync.smartabase.com/ssi/?#Home');
  await page.locator('span').filter({ hasText: 'Data Entry' }).click();
  await page.locator('a').filter({ hasText: 'Import Data' }).click();
  await page.locator('#dropdown-formselector-4').selectOption('7550');
  // await page.getByRole('button', { name: 'Choose File' }).click();
  await page.getByRole('button', { name: 'Choose File' }).setInputFiles('templates/templates.csv');
  await page.getByRole('button', { name: 'Upload' }).click();
  await page.goto('https://sportsync.smartabase.com/ssi/?#Home.Import-Data.Confirm-Athletes');
  await page.getByRole('combobox').selectOption('First Name');
  await page.getByRole('button', { name: 'Add Identifier' }).click();
  await page.getByRole('combobox').nth(1).selectOption('Last Name');
  await page.getByRole('button', { name: 'Next' }).click();
  await page.getByRole('combobox').nth(2).selectOption('dd-MM-yy e.g 15-11-08');
  page.once('dialog', dialog => {
    console.log(`Dialog message: ${dialog.message()}`);
    dialog.dismiss().catch(() => {});
  });
  await page.getByRole('cell', { name: 'Date Format : dd-MM-yy e.g 15' }).locator('#test').click();
  await page.locator('div:nth-child(8) > .form-item > tbody > tr > td:nth-child(2) > .directional-panel-container-horizontal.align-horizontal-left > .directional-panel-container-horizontal > .select-box-wrapper > .gwt-ListBox').selectOption('dd-MM-yy e.g 15-11-08');
  page.once('dialog', dialog => {
    console.log(`Dialog message: ${dialog.message()}`);
    dialog.dismiss().catch(() => {});
  });
  await page.getByRole('cell', { name: 'Visit Date Format : dd-MM-yy' }).locator('#test').click();
  await page.locator('div:nth-child(6) > div > .form-item > tbody > tr > td:nth-child(2) > .directional-panel-container-horizontal.align-horizontal-left > .directional-panel-container-horizontal > .select-box-wrapper > .gwt-ListBox').selectOption('dd-MM-yy e.g 15-11-08');
  page.once('dialog', dialog => {
    console.log(`Dialog message: ${dialog.message()}`);
    dialog.dismiss().catch(() => {});
  });
  await page.getByRole('cell', { name: 'Format : dd-MM-yy e.g 15-11-08 Test', exact: true }).locator('#test').click();
  await page.locator('#dropdown-column-11').selectOption('Date');
  page.once('dialog', dialog => {
    console.log(`Dialog message: ${dialog.message()}`);
    dialog.dismiss().catch(() => {});
  });
  await page.getByRole('button', { name: 'Test' }).nth(2).click();
  await page.locator('#dropdown-column-12').selectOption('Time');
  await page.getByRole('checkbox', { name: 'Import data that appears to' }).check();
  await page.getByRole('button', { name: 'Next' }).click();
  await page.getByRole('combobox').selectOption('Skip sending any performance alerts');
  await page.getByRole('button', { name: 'Import' }).click();
  await page.locator('i').nth(4).click();
  await page.locator('#logout').click();
});