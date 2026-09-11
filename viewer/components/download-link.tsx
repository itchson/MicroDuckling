"use client";

import { useEffect, useState, type ComponentPropsWithoutRef } from "react";
import { Button } from "@/components/ui/button";

type Props = ComponentPropsWithoutRef<"a"> & { href: string };

/** Only offer an export after the local server confirms that the file exists. */
export function DownloadLink({ href, children, className = "", ...props }: Props) {
  const [state, setState] = useState<"checking" | "ready" | "missing">("checking");

  useEffect(() => {
    const controller = new AbortController();
    setState("checking");
    void fetch(href, { method: "HEAD", cache: "no-store", signal: controller.signal })
      .then((response) => {
        // Some development servers return the application's HTML for a missing asset.
        const isUnexpectedHtml = response.headers.get("content-type")?.includes("text/html") && !/\.html?(?:$|\?)/i.test(href);
        const isEmpty = response.headers.get("content-length") === "0";
        setState(response.ok && !isUnexpectedHtml && !isEmpty ? "ready" : "missing");
      })
      .catch(() => { if (!controller.signal.aborted) setState("missing"); });
    return () => controller.abort();
  }, [href]);

  if (state === "ready") return <a href={href} className={className} {...props}>{children}</a>;
  return <Button
    variant="ghost"
    disabled
    className={`download-unavailable ${className}`}
    title={state === "checking" ? "Checking this file" : "File unavailable. Reload after generating the exports."}
  >{children}<span className="download-state">{state === "checking" ? "Checking…" : "Unavailable"}</span></Button>;
}
