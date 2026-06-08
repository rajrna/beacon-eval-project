import { useState } from "react";
import {
  useParams,
  useNavigate,
  Link,
} from "react-router-dom";
import {
  ArrowLeft,
  Plus,
  Lock,
  Unlock,
  PlayCircle,
  ChevronRight,
  GitCompare,
} from "lucide-react";
import {
  useAgent,
  useAgentVersions,
  useCreateAgentVersion,
  useEvalRun,
} from "@/lib/api/hooks";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type {
  Paginated,
  EvalRun,
} from "@/lib/api/types";
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Spinner,
  Dialog,
  Input,
  Textarea,
  Select,
  Table,
  Thead,
  Tbody,
  Th,
  Td,
  PageHeader,
  EmptyState,
} from "@/components/ui";
import {
  formatDate,
  formatScore,
  statusColor,
  cn,
} from "@/lib/utils";
import { RunTriggerModal } from "@/components/eval/RunTriggerModal";

function useAgentRuns(agentVersionIds: string[]) {
  return useQuery({
    queryKey: ["agent-runs", agentVersionIds],
    queryFn: async () => {
      if (!agentVersionIds.length)
        return { items: [], total: 0 };
      // Fetch runs for the latest few versions
      const results = await Promise.all(
        agentVersionIds.slice(0, 5).map((id) =>
          api
            .get<
              Paginated<EvalRun>
            >(`/v1/runs?agent_version_id=${id}&limit=5`)
            .catch(() => ({
              items: [],
              total: 0,
            })),
        ),
      );
      const allRuns = results.flatMap(
        (r: any) => r.items || [],
      );
      allRuns.sort(
        (a: EvalRun, b: EvalRun) =>
          new Date(b.created_at).getTime() -
          new Date(a.created_at).getTime(),
      );
      return {
        items: allRuns.slice(0, 10),
        total: allRuns.length,
      };
    },
    enabled: agentVersionIds.length > 0,
  });
}

function NewVersionModal({
  agentId,
  open,
  onClose,
}: {
  agentId: string;
  open: boolean;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    system_prompt: "",
    model_id: "claude-sonnet-4-5",
    temperature: "0.0",
    max_tokens: "1024",
    notes: "",
  });
  const create = useCreateAgentVersion(agentId);

  const handleSubmit = async () => {
    await create.mutateAsync({
      system_prompt: form.system_prompt,
      model_id: form.model_id,
      temperature: parseFloat(form.temperature),
      max_tokens: parseInt(form.max_tokens),
      notes: form.notes || undefined,
    });
    onClose();
    setForm({
      system_prompt: "",
      model_id: "claude-sonnet-4-5",
      temperature: "0.0",
      max_tokens: "1024",
      notes: "",
    });
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="New Agent Version"
      size="xl"
    >
      <div className="space-y-4">
        <Textarea
          label="System Prompt"
          rows={10}
          value={form.system_prompt}
          onChange={(e) =>
            setForm((f) => ({
              ...f,
              system_prompt: e.target.value,
            }))
          }
          placeholder="You are a helpful enrollment advisor for..."
        />
        <div className="grid grid-cols-3 gap-4">
          <Select
            label="Model"
            value={form.model_id}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                model_id: e.target.value,
              }))
            }
            options={[
              {
                value: "claude-sonnet-4-5",
                label: "Claude Sonnet 4.5",
              },
              {
                value: "claude-opus-4-5",
                label: "Claude Opus 4.5",
              },
              {
                value:
                  "global.anthropic.claude-haiku-4-5-20251001-v1:0",
                label:
                  "Claude 3.5 Haiku (Bedrock)",
              },
              {
                value:
                  "anthropic.claude-3-5-sonnet-20241022-v2:0",
                label:
                  "Claude 3.5 Sonnet (Bedrock)",
              },
            ]}
          />
          <Input
            label="Temperature"
            type="number"
            min="0"
            max="1"
            step="0.1"
            value={form.temperature}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                temperature: e.target.value,
              }))
            }
          />
          <Input
            label="Max Tokens"
            type="number"
            min="256"
            max="8192"
            value={form.max_tokens}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                max_tokens: e.target.value,
              }))
            }
          />
        </div>
        <Textarea
          label="Version Notes (optional)"
          rows={2}
          value={form.notes}
          onChange={(e) =>
            setForm((f) => ({
              ...f,
              notes: e.target.value,
            }))
          }
          placeholder="What changed in this version..."
        />
        <div className="flex justify-end gap-3 pt-2">
          <Button
            variant="outline"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            loading={create.isPending}
            disabled={!form.system_prompt}
          >
            Create Version
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

export default function AgentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [newVersionOpen, setNewVersionOpen] =
    useState(false);
  const [runModalOpen, setRunModalOpen] =
    useState(false);

  const { data: agent, isLoading } = useAgent(
    id!,
  );
  const { data: versions } = useAgentVersions(
    id!,
  );

  const versionIds =
    versions?.items?.map((v) => v.id) ?? [];
  const { data: recentRuns } =
    useAgentRuns(versionIds);

  if (isLoading)
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  if (!agent)
    return (
      <div className="text-center py-20 text-gray-500">
        Agent not found
      </div>
    );

  const roleColors: Record<string, string> = {
    advisor:
      "bg-blue-900/30 text-blue-400 border-blue-800",
    outreach:
      "bg-purple-900/30 text-purple-400 border-purple-800",
    retention:
      "bg-orange-900/30 text-orange-400 border-orange-800",
    finaid:
      "bg-green-900/30 text-green-400 border-green-800",
    career:
      "bg-cyan-900/30 text-cyan-400 border-cyan-800",
    tutor:
      "bg-pink-900/30 text-pink-400 border-pink-800",
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="text-gray-500 hover:text-gray-300"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <PageHeader
          title={agent.name}
          description={`${agent.version_count} version${agent.version_count !== 1 ? "s" : ""} · ${agent.owner_team ?? "No team assigned"}`}
          action={
            <div className="flex gap-2">
              <Button
                variant="ghost"
                onClick={() =>
                  navigate(
                    `/agents/${id}/compare`,
                  )
                }
              >
                <GitCompare className="h-4 w-4" />{" "}
                Compare
              </Button>
              <Button
                variant="outline"
                onClick={() =>
                  setRunModalOpen(true)
                }
              >
                <PlayCircle className="h-4 w-4" />{" "}
                Run Eval
              </Button>
              <Button
                onClick={() =>
                  setNewVersionOpen(true)
                }
              >
                <Plus className="h-4 w-4" /> New
                Version
              </Button>
            </div>
          }
        />
      </div>

      {/* Agent info */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: "Role",
            value: (
              <span
                className={cn(
                  "text-xs px-2 py-0.5 rounded-full border",
                  roleColors[agent.role] ??
                    "bg-gray-800 text-gray-400 border-gray-700",
                )}
              >
                {agent.role}
              </span>
            ),
          },
          {
            label: "Status",
            value: (
              <Badge
                variant={
                  agent.is_active
                    ? "success"
                    : "default"
                }
              >
                {agent.is_active
                  ? "Active"
                  : "Inactive"}
              </Badge>
            ),
          },
          {
            label: "Owner Email",
            value: (
              <span className="text-sm text-gray-300">
                {agent.owner_email ?? "—"}
              </span>
            ),
          },
          {
            label: "Created",
            value: (
              <span className="text-sm text-gray-400">
                {formatDate(agent.created_at)}
              </span>
            ),
          },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardContent className="py-3">
              <p className="text-xs text-gray-500 mb-1">
                {label}
              </p>
              {value}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Versions */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Versions</CardTitle>
                <Button
                  size="sm"
                  onClick={() =>
                    setNewVersionOpen(true)
                  }
                >
                  <Plus className="h-3.5 w-3.5" />{" "}
                  New
                </Button>
              </div>
            </CardHeader>
            {!versions?.items?.length ? (
              <CardContent>
                <EmptyState
                  title="No versions yet"
                  description="Create the first version of this agent."
                  action={
                    <Button
                      onClick={() =>
                        setNewVersionOpen(true)
                      }
                    >
                      Create Version
                    </Button>
                  }
                />
              </CardContent>
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th>Version</Th>
                    <Th>Model</Th>
                    <Th>Temp</Th>
                    <Th>Status</Th>
                    <Th>Created</Th>
                    <Th></Th>
                  </tr>
                </Thead>
                <Tbody>
                  {versions.items.map((v) => (
                    <tr
                      key={v.id}
                      className="cursor-pointer hover:bg-white/5 border-b border-white/5 transition-colors"
                      onClick={() =>
                        navigate(
                          `/agents/${id}/versions/${v.id}`,
                        )
                      }
                    >
                      <Td>
                        <span className="font-mono font-semibold text-gray-200">
                          v{v.version_number}
                        </span>
                        {v.id ===
                          agent.latest_version_id && (
                          <span className="ml-2 text-xs bg-indigo-900/40 text-indigo-400 border border-indigo-800 px-1.5 py-0.5 rounded-full">
                            latest
                          </span>
                        )}
                      </Td>
                      <Td>
                        <code className="text-xs text-gray-400">
                          {v.model_id}
                        </code>
                      </Td>
                      <Td className="text-gray-400 text-sm">
                        {v.temperature}
                      </Td>
                      <Td>
                        {v.is_locked ? (
                          <div className="flex items-center gap-1 text-xs text-gray-500">
                            <Lock className="h-3 w-3" />{" "}
                            Locked
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-xs text-green-500">
                            <Unlock className="h-3 w-3" />{" "}
                            Editable
                          </div>
                        )}
                      </Td>
                      <Td className="text-gray-500 text-xs">
                        {formatDate(v.created_at)}
                      </Td>
                      <Td>
                        <ChevronRight className="h-4 w-4 text-gray-600" />
                      </Td>
                    </tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </Card>
        </div>

        {/* Recent runs */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle>
                Recent Eval Runs
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {!recentRuns?.items?.length ? (
                <div className="px-6 py-8">
                  <EmptyState
                    title="No runs yet"
                    description="Trigger an eval run to see results."
                  />
                </div>
              ) : (
                <div className="divide-y divide-white/5">
                  {recentRuns.items.map(
                    (run: EvalRun) => (
                      <div
                        key={run.id}
                        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-white/5"
                        onClick={() =>
                          navigate(
                            `/runs/${run.id}`,
                          )
                        }
                      >
                        <div>
                          <p className="text-xs font-mono text-gray-400">
                            {run.id.slice(0, 8)}…
                          </p>
                          <p className="text-xs text-gray-600 mt-0.5">
                            {formatDate(
                              run.created_at,
                            )}
                          </p>
                        </div>
                        <div className="text-right">
                          <span
                            className={cn(
                              "text-xs px-2 py-0.5 rounded-full",
                              statusColor(
                                run.status,
                              ),
                            )}
                          >
                            {run.status}
                          </span>
                          {run.pass_rate !=
                            null && (
                            <p
                              className={cn(
                                "text-sm font-bold mt-1",
                                run.pass_rate >=
                                  0.8
                                  ? "text-green-400"
                                  : run.pass_rate >=
                                      0.6
                                    ? "text-yellow-400"
                                    : "text-red-400",
                              )}
                            >
                              {formatScore(
                                run.pass_rate,
                              )}
                            </p>
                          )}
                        </div>
                      </div>
                    ),
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <NewVersionModal
        agentId={id!}
        open={newVersionOpen}
        onClose={() => setNewVersionOpen(false)}
      />
      <RunTriggerModal
        open={runModalOpen}
        onClose={() => setRunModalOpen(false)}
        onSuccess={(runId) =>
          navigate(`/runs/${runId}`)
        }
      />
    </div>
  );
}
