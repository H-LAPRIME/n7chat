/**
 * app/page.tsx
 * Root redirect → /login
 */
import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/login");
}
