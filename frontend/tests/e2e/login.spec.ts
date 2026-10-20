import { expect, test } from '@playwright/test'

test('admin can log in, refresh the session, and log out', async ({ page }) => {
  await page.goto('/login')

  await page.getByLabel('租户').fill('acme')
  await page.getByLabel('邮箱').fill('admin@example.com')
  await page.getByLabel('密码').fill('Admin123!')
  await page.getByRole('button', { name: '登录' }).click()

  await expect(page).toHaveURL('/')
  await expect(
    page.getByRole('heading', { name: 'LexPilot 工作台' }),
  ).toBeVisible()
  await expect(page.getByText('admin@example.com').first()).toBeVisible()

  // 刷新页面后通过 HttpOnly Refresh Cookie 恢复会话
  await page.reload()
  await expect(
    page.getByRole('heading', { name: 'LexPilot 工作台' }),
  ).toBeVisible()

  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page).toHaveURL('/login')
})

test('invalid credentials show a clear error', async ({ page }) => {
  await page.goto('/login')

  await page.getByLabel('租户').fill('acme')
  await page.getByLabel('邮箱').fill('admin@example.com')
  await page.getByLabel('密码').fill('wrong-password')
  await page.getByRole('button', { name: '登录' }).click()

  await expect(page.getByText('邮箱或密码错误')).toBeVisible()
  await expect(page).toHaveURL('/login')
})
