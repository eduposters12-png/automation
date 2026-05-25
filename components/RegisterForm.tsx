"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api";
import type { AuthResponse } from "@/lib/types";

export function RegisterForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setLoading(true);
    try {
      await apiFetch<AuthResponse>("/auth/register", {
        method: "POST",
        json: {
          name: formData.get("name"),
          email: formData.get("email"),
          password: formData.get("password")
        }
      });
      toast.success("Account created");
      router.push("/onboarding");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <Input label="Name" name="name" type="text" autoComplete="name" required />
      <Input label="Email" name="email" type="email" autoComplete="email" required />
      <Input label="Password" name="password" type="password" autoComplete="new-password" minLength={8} required />
      <Button type="submit" loading={loading} className="w-full">
        Create account
      </Button>
    </form>
  );
}
