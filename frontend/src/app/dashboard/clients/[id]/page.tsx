import { ClientDetail } from "@/components/client-detail";
import { serverApi } from "@/lib/server-api";
import type { ProcessDetail } from "@/lib/types";

export default async function ClientPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const process = await serverApi<ProcessDetail>(
    `/admin/processes/${encodeURIComponent(id)}`,
  );
  return <ClientDetail process={process} />;
}
