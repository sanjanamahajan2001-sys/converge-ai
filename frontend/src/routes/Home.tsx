import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import { Card } from '@/components/ui/Card';
import { StatusBadge, StatusVariant } from '@/components/ui/StatusBadge';
import { LoadingState } from '@/components/ui/LoadingState';

export const Home: React.FC = () => {
  const {
    data: health,
    isLoading: isHealthLoading,
    isError: isHealthError,
    error: healthError,
  } = useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval: 30000,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  const {
    data: readiness,
    isLoading: isReadinessLoading,
    isError: isReadinessError,
    error: readinessError,
  } = useQuery({
    queryKey: ['readiness'],
    queryFn: api.getReadiness,
    refetchInterval: 30000,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  const {
    data: version,
    isLoading: isVersionLoading,
    isError: isVersionError,
  } = useQuery({
    queryKey: ['version'],
    queryFn: api.getVersion,
    staleTime: 60000,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  // Calculate truthful engine status
  const isEngineOperational = health?.status === 'healthy' && !isHealthError;

  // Calculate truthful database status based solely on live readiness response
  let dbVariant: StatusVariant = 'neutral';
  let dbEmoji = '⏳';
  let dbLabel = 'Probing...';
  let dbDetail = 'Verifying database connectivity pool...';

  if (isReadinessLoading) {
    dbVariant = 'neutral';
    dbEmoji = '⏳';
    dbLabel = 'Checking';
    dbDetail = 'Sending readiness probe to /converge-api/v1/health/ready...';
  } else if (isReadinessError) {
    dbVariant = 'danger';
    dbEmoji = '🔴';
    dbLabel = 'Offline';
    dbDetail = readinessError instanceof Error ? readinessError.message : 'Backend connection failed';
  } else if (readiness) {
    if (readiness.database === 'connected' && readiness.status === 'ready') {
      dbVariant = 'success';
      dbEmoji = '🟢';
      dbLabel = 'Connected';
      dbDetail = 'PostgreSQL connection pool active and accepting queries';
    } else if (readiness.database === 'unconfigured') {
      dbVariant = 'warning';
      dbEmoji = '🟡';
      dbLabel = 'Unconfigured';
      dbDetail = 'DATABASE_URL is not configured in backend environment';
    } else {
      dbVariant = 'danger';
      dbEmoji = '🔴';
      dbLabel = 'Disconnected';
      dbDetail = 'PostgreSQL daemon unreachable or connection refused';
    }
  }

  const isAnyLoading = isHealthLoading || isReadinessLoading || isVersionLoading;

  return (
    <div className="space-y-10 sm:space-y-12">
      {/* Editorial Hero Composition */}
      <section className="border-b border-canvas-border pb-8 sm:pb-12" aria-labelledby="hero-heading">
        <div className="max-w-5xl">
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <StatusBadge emoji="🌿" label="Physical Conferences" variant="neutral" />
            <StatusBadge emoji="🤖" label="Agent-to-Agent Network" variant="warning" />
            <StatusBadge emoji="🔒" label="Dual Consent Gated" variant="neutral" />
          </div>
          <h1
            id="hero-heading"
            className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-ink-primary leading-[1.15]"
          >
            Autonomous Background Networking for Conference Delegates
          </h1>
          <p className="mt-4 sm:mt-5 text-base sm:text-lg text-ink-secondary leading-relaxed font-sans">
            Converge AI pairs each registered conference participant with a personal AI agent that explores shared technical interests, cross-checks session availability, and coordinates informal coffee discussions in the background under strict dual-human approval.
          </p>
        </div>
      </section>

      {/* Live System Telemetry Section */}
      <section aria-labelledby="telemetry-heading" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1">
          <div>
            <h2 id="telemetry-heading" className="font-serif text-xl sm:text-2xl font-bold text-ink-primary flex items-center gap-2">
              <span aria-hidden="true">📡</span> Live Infrastructure Telemetry
            </h2>
            <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
              Live responses sourced directly from local backend probes on port 8030.
            </p>
          </div>
          <span className="text-[11px] font-mono text-ink-muted">
            Auto-refresh: 30s
          </span>
        </div>

        {isAnyLoading && !health && !readiness ? (
          <LoadingState message="Connecting to local backend on 127.0.0.1:8030..." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 sm:gap-6">
            {/* Telemetry Card 1: Application Engine */}
            <Card
              title="Application Engine"
              subtitle="Process Liveness Probe"
              badge={
                <StatusBadge
                  emoji={isEngineOperational ? '🟢' : '🔴'}
                  label={isEngineOperational ? 'Operational' : 'Unreachable'}
                  variant={isEngineOperational ? 'success' : 'danger'}
                />
              }
            >
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-canvas-border/50">
                  <span className="text-ink-muted">Probe Target</span>
                  <span className="font-mono text-ink-primary">/converge-api/v1/health</span>
                </div>
                <div className="flex justify-between py-1 border-b border-canvas-border/50">
                  <span className="text-ink-muted">Service Name</span>
                  <span className="font-mono text-ink-primary">{health?.service || (isHealthError ? 'offline' : '—')}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-canvas-border/50">
                  <span className="text-ink-muted">Environment</span>
                  <span className="font-mono text-ink-primary uppercase">{health?.environment || (isHealthError ? 'offline' : '—')}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-ink-muted">Probe Result</span>
                  <span className="font-mono text-ink-primary">
                    {isEngineOperational ? 'HTTP 200 (healthy)' : (healthError ? 'Connection Refused' : 'Checking')}
                  </span>
                </div>
              </div>
            </Card>

            {/* Telemetry Card 2: Database Connectivity */}
            <Card
              title="Database Pool"
              subtitle="Infrastructure Readiness Probe"
              badge={
                <StatusBadge
                  emoji={dbEmoji}
                  label={dbLabel}
                  variant={dbVariant}
                />
              }
            >
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-canvas-border/50">
                  <span className="text-ink-muted">Probe Target</span>
                  <span className="font-mono text-ink-primary">/converge-api/v1/health/ready</span>
                </div>
                <div className="flex justify-between py-1 border-b border-canvas-border/50">
                  <span className="text-ink-muted">Live DB State</span>
                  <span className="font-mono text-ink-primary font-semibold capitalize">
                    {readiness?.database || (isReadinessError ? 'offline' : 'checking')}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-canvas-border/50">
                  <span className="text-ink-muted">Readiness State</span>
                  <span className="font-mono text-ink-primary">
                    {readiness?.status ? `${readiness.status}` : (isReadinessError ? 'failed' : '—')}
                  </span>
                </div>
                <div className="pt-1">
                  <p className="text-[11px] text-ink-secondary leading-snug">
                    {dbDetail}
                  </p>
                </div>
              </div>
            </Card>

            {/* Telemetry Card 3: Gateway & Versioning */}
            <Card
              title="Gateway & Software"
              subtitle="Package Version Metadata"
              badge={
                <StatusBadge
                  emoji={version ? '🟢' : (isVersionError ? '🔴' : '⏳')}
                  label={version ? 'Reported' : (isVersionError ? 'Unreachable' : 'Checking')}
                  variant={version ? 'success' : (isVersionError ? 'danger' : 'neutral')}
                />
              }
            >
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-canvas-border/50">
                  <span className="text-ink-muted">Probe Target</span>
                  <span className="font-mono text-ink-primary">/converge-api/v1/version</span>
                </div>
                <div className="flex justify-between py-1 border-b border-canvas-border/50">
                  <span className="text-ink-muted">Semantic Version</span>
                  <span className="font-mono text-ink-primary font-semibold">
                    {version?.version ? `v${version.version}` : '—'}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-canvas-border/50">
                  <span className="text-ink-muted">Gateway Prefix</span>
                  <span className="font-mono text-ink-primary">{version?.api_prefix || '/converge-api/v1'}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-ink-muted">Frontend Base</span>
                  <span className="font-mono text-ink-primary">/converge/</span>
                </div>
              </div>
            </Card>
          </div>
        )}
      </section>

      {/* Static Architecture Baseline (Explicitly Non-Telemetry) */}
      <section aria-labelledby="architecture-heading" className="space-y-4">
        <div>
          <h2 id="architecture-heading" className="font-serif text-xl sm:text-2xl font-bold text-ink-primary flex items-center gap-2">
            <span aria-hidden="true">🏛️</span> Verified Architecture Baseline
          </h2>
          <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
            Static specifications verified for the system architecture foundation.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
          <Card
            title="Database Privilege Model"
            subtitle="Security Architecture (GAP-02)"
            badge={<StatusBadge emoji="🛡️" label="Role Separation" variant="neutral" />}
          >
            <p className="text-xs text-ink-secondary leading-relaxed mb-3">
              PostgreSQL access strictly enforces two distinct database roles to prevent migration privilege leakage:
            </p>
            <div className="space-y-2 text-xs font-mono bg-canvas-elevated p-3 rounded border border-canvas-border">
              <div className="flex justify-between">
                <span className="text-ink-muted">Migration/DDL Role:</span>
                <span className="text-ink-primary font-semibold">converge_ai_owner</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-muted">Runtime/DML Role:</span>
                <span className="text-ink-primary font-semibold">converge_ai_app</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-muted">DDL Execution Privilege:</span>
                <span className="text-sage font-semibold">Blocked for Runtime Role</span>
              </div>
            </div>
          </Card>

          <Card
            title="Provisioned Schemas"
            subtitle="Alembic Baseline Migration 001"
            badge={<StatusBadge emoji="📦" label="Schemas Created" variant="neutral" />}
          >
            <p className="text-xs text-ink-secondary leading-relaxed mb-3">
              The four foundational domain schemas provisioned for the conference network:
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-2 bg-canvas-elevated rounded border border-canvas-border">
                <div className="font-semibold text-ink-primary">core</div>
                <div className="text-[10px] text-ink-muted mt-0.5">Participants & Auth</div>
              </div>
              <div className="p-2 bg-canvas-elevated rounded border border-canvas-border">
                <div className="font-semibold text-ink-primary">agenda</div>
                <div className="text-[10px] text-ink-muted mt-0.5">Sessions & Tracks</div>
              </div>
              <div className="p-2 bg-canvas-elevated rounded border border-canvas-border">
                <div className="font-semibold text-ink-primary">matching</div>
                <div className="text-[10px] text-ink-muted mt-0.5">Scores & Proposals</div>
              </div>
              <div className="p-2 bg-canvas-elevated rounded border border-canvas-border">
                <div className="font-semibold text-ink-primary">a2a</div>
                <div className="text-[10px] text-ink-muted mt-0.5">Agent Tasks & Convo</div>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* Planned Capabilities & Roadmap */}
      <section aria-labelledby="roadmap-heading" className="space-y-4">
        <div>
          <h2 id="roadmap-heading" className="font-serif text-xl sm:text-2xl font-bold text-ink-primary flex items-center gap-2">
            <span aria-hidden="true">📋</span> Planned Engineering Roadmap
          </h2>
          <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
            Core capability status following the conference platform specifications.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 sm:gap-6">
          <Card
            title="Participant Profiles & Authentication"
            subtitle="Participant Identity"
            badge={<StatusBadge emoji="⏳" label="Planned" variant="warning" />}
          >
            <p className="text-xs text-ink-secondary leading-relaxed mb-3">
              Participant registration with unique usernames, networking vs casual intent, beverage preferences (☕ Tea/Coffee), and privacy controls.
            </p>
            <div className="text-[11px] font-mono text-ink-muted border-t border-canvas-border pt-2">
              Deliverables: Auth cookies, profile CRUD, topic tags
            </div>
          </Card>

          <Card
            title="Conference Agenda & Sessions"
            subtitle="Session Integration"
            badge={<StatusBadge emoji="⏳" label="Planned" variant="warning" />}
          >
            <p className="text-xs text-ink-secondary leading-relaxed mb-3">
              Real conference schedule ingestion, speaker profiles, room assignments, and participant session bookmarking for agent matching context.
            </p>
            <div className="text-[11px] font-mono text-ink-muted border-t border-canvas-border pt-2">
              Deliverables: Agenda API, bookmarking, conflict check
            </div>
          </Card>

          <Card
            title="Intelligent Matching & Agent Network"
            subtitle="Autonomous Agents"
            badge={<StatusBadge emoji="⏳" label="Planned" variant="warning" />}
          >
            <p className="text-xs text-ink-secondary leading-relaxed mb-3">
              Deterministic matching engine scoring shared interests and schedules, followed by official A2A protocol v1.0.0 background conversations.
            </p>
            <div className="text-[11px] font-mono text-ink-muted border-t border-canvas-border pt-2">
              Deliverables: Matchmaker, A2A v1.0 adapter (GAP-01)
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
};
