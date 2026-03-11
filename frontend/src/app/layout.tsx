import "../styles/globals.css"

export const metadata = {
  title: "Analytica",
  description: "AI SaaS Dashboard"
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {

  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  )

}