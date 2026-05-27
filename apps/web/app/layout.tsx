export const metadata = { title: 'Recurring Payments', description: 'Recurring Payments Dashboard' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
