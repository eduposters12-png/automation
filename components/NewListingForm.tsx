"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api";
import type { Job } from "@/lib/types";

export function NewListingForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const price = String(formData.get("target_price") || "");
    setLoading(true);
    try {
      await apiFetch<Job>("/jobs/generate-listing", {
        method: "POST",
        json: {
          product_idea: formData.get("product_idea"),
          target_price: price ? price : undefined
        }
      });
      toast.success("Listing job queued");
      router.push("/listings");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not queue listing");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="max-w-2xl">
      <form className="space-y-4" onSubmit={onSubmit}>
        <Input
          label="Product idea"
          name="product_idea"
          placeholder="Printable wedding seating chart template"
          required
          minLength={3}
        />
        <Input
          label="Target price"
          name="target_price"
          type="number"
          min="0"
          step="0.01"
          placeholder="9.99"
        />
        <Button type="submit" loading={loading}>
          Queue listing
        </Button>
      </form>
    </Card>
  );
}
