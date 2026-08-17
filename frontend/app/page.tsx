"use client";

import {
  FormEvent,
  MouseEvent,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

type StockStatus = "RECEIVING" | "AVAILABLE" | "RESERVED" | "DAMAGED";
type InventoryBalance = {
  product_id: string;
  seller_id: string;
  warehouse_id: string;
  location_id: string;
  stock_status: StockStatus;
  quantity: number;
  updated_at: string;
};
type Seller = { id: string; name: string; code: string };
type Warehouse = {
  id: string;
  name: string;
  code: string;
  city: string;
  state: string;
};
type Location = {
  id: string;
  name: string;
  code: string;
  warehouse_id: string;
};
type Product = {
  id: string;
  name: string;
  sku: string;
  barcode: string;
  seller_id: string;
};
type Receipt = {
  id: string;
  seller_id: string;
  warehouse_id: string;
  reference_type: string;
  reference_value: string;
  status: string;
  line_count: number;
  created_at: string;
};
type Order = {
  id: string;
  seller_id: string;
  warehouse_id: string;
  order_number: string;
  source: string;
  status: string;
  item_count: number;
  created_at: string;
};
type AppUser = {
  id: string;
  name: string;
  email: string;
  organization_id: string;
  role: "user" | "staff" | "manager" | "admin";
  active: boolean;
};
type Session = { access_token: string; user: AppUser };
type ApiRequest = <T>(
  path: string,
  options?: RequestInit,
  needsActor?: boolean,
) => Promise<T>;
type Shipment = {
  id: string;
  order_id: string;
  order_number: string;
  carrier_id: string;
  carrier_name: string;
  service_level: string;
  tracking_number: string;
  status: string;
  ship_to: {
    name: string;
    line1: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
  events: Array<{
    status: string;
    location?: string;
    note?: string;
    occurred_at: string;
  }>;
  created_at: string;
};
type Invoice = {
  id: string;
  invoice_number: string;
  order_id: string;
  order_number: string;
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
  currency: string;
  status: string;
  due_at: string;
  created_at: string;
};
type Payment = {
  id: string;
  invoice_id: string;
  provider: string;
  provider_payment_id?: string;
  amount_cents: number;
  currency: string;
  status: string;
  client_secret?: string;
  created_at: string;
};
type KnowledgeDocument = {
  id: string;
  filename: string;
  content_type: string;
  character_count: number;
  chunk_count: number;
  created_at: string;
};
type AssistantSource = {
  document_id: string;
  filename: string;
  chunk_index: number;
  excerpt: string;
  score: number;
};
type AssistantMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: AssistantSource[];
  mode?: string;
};
type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult:
    | ((event: { results: ArrayLike<{ 0: { transcript: string } }> }) => void)
    | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
};

// Browser requests stay same-origin through the Next.js proxy. This avoids a
// fragile CORS dependency when the frontend is started on a different port.
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";
const websocketBaseUrl =
  process.env.NEXT_PUBLIC_WEBSOCKET_BASE_URL ?? "ws://localhost:8001/api/v1";
const navigation = [
  ["Overview", "grid"],
  ["Orders", "package"],
  ["Receiving", "inbox"],
  ["Inventory", "layers"],
  ["Shipping", "package"],
  ["Billing", "inbox"],
  ["Setup", "settings"],
  ["Users", "settings"],
] as const;

function Icon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    package: (
      <>
        <path d="m21 8-9 5-9-5 9-5 9 5Z" />
        <path d="M3 8v8l9 5 9-5V8" />
        <path d="M12 13v8" />
      </>
    ),
    inbox: (
      <>
        <path d="M4 4h16v12l-3 3H7l-3-3V4Z" />
        <path d="M4 13h5l1.5 2h3L15 13h5" />
      </>
    ),
    layers: (
      <>
        <path d="m12 3 9 5-9 5-9-5 9-5Z" />
        <path d="m3 12 9 5 9-5" />
        <path d="m3 17 9 5 9-5" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.2 2.2-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56v.1h-3.1v-.1A1.7 1.7 0 0 0 10.5 18.7a1.7 1.7 0 0 0-1.88.34l-.06.06-2.2-2.2.06-.06A1.7 1.7 0 0 0 6.76 15a1.7 1.7 0 0 0-1.56-1.03h-.1v-3.1h.1A1.7 1.7 0 0 0 6.76 9.8a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.2-2.2.06.06a1.7 1.7 0 0 0 1.88.34 1.7 1.7 0 0 0 1.03-1.56v-.1h3.1v.1a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.2 2.2-.06.06a1.7 1.7 0 0 0-.34 1.88 1.7 1.7 0 0 0 1.56 1.03h.1v3.1h-.1A1.7 1.7 0 0 0 19.4 15Z" />
      </>
    ),
  };
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

function StatusPill({
  label,
  tone = "blue",
}: {
  label: string;
  tone?: "green" | "amber" | "blue" | "slate";
}) {
  return (
    <span className={`pill pill-${tone}`}>
      <span className="pill-dot" />
      {label}
    </span>
  );
}

function readableError(error: unknown) {
  if (error instanceof Error) return error.message;
  return "The request could not be completed.";
}

function createOrderNumber() {
  const now = new Date();
  const date = now.toISOString().slice(2, 10).replaceAll("-", "");
  const suffix = crypto.randomUUID().slice(0, 6).toUpperCase();
  return `WMS-${date}-${suffix}`;
}

function hasExpiredAccessToken(token: string) {
  try {
    const payload = token.split(".")[1];
    if (!payload) return true;
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(atob(normalized)) as { exp?: unknown };
    return typeof decoded.exp !== "number" || decoded.exp * 1000 <= Date.now();
  } catch {
    return true;
  }
}

export default function WmsApp() {
  const [isLoading, setIsLoading] = useState(true);
  const [organizationId, setOrganizationId] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [activeNav, setActiveNav] =
    useState<(typeof navigation)[number][0]>("Overview");
  const [apiState, setApiState] = useState<"loading" | "online" | "offline">(
    "loading",
  );
  const [notice, setNotice] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [balances, setBalances] = useState<InventoryBalance[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [users, setUsers] = useState<AppUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [assistantOpen, setAssistantOpen] = useState(false);

  const request = useCallback(
    async <T,>(
      path: string,
      options: RequestInit = {},
      needsActor = false,
    ): Promise<T> => {
      const headers = new Headers(options.headers);
      if (!session) throw new Error("Please sign in again");
      headers.set("Authorization", `Bearer ${session.access_token}`);
      headers.set("X-Organization-Id", session.user.organization_id);
      if (options.body) headers.set("Content-Type", "application/json");
      if (needsActor) {
        headers.set("Idempotency-Key", crypto.randomUUID());
      }
      const response = await fetch(`${apiBaseUrl}${path}`, {
        ...options,
        headers,
      });
      const body = await response.json().catch(() => null);
      if (response.status === 401) {
        // A stale token must never leave the user on a broken dashboard with
        // empty selectors and an "Offline" badge. Clear it immediately and
        // send the user to the one place where a new token can be issued.
        localStorage.removeItem("whitfield_session");
        setSession(null);
        setOrganizationId("");
        setShowAuth(true);
        setIsLoading(false);
        throw new Error("Your session expired. Please sign in again.");
      }
      if (!response.ok) {
        const detail =
          typeof body?.detail === "string"
            ? body.detail
            : Array.isArray(body?.detail)
              ? body.detail
                  .map(
                    (item: { loc?: string[]; msg?: string }) =>
                      `${item.loc?.at(-1) ?? "field"}: ${item.msg ?? "is invalid"}`,
                  )
                  .join("; ")
              : (body?.detail?.code ?? "Request failed");
        throw new Error(detail);
      }
      return body as T;
    },
    [session],
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      if (!session) return;
      const [
        inventory,
        sellerList,
        warehouseList,
        locationList,
        productList,
        receiptList,
        orderList,
        shipmentList,
        invoiceList,
        paymentList,
      ] = await Promise.all([
        request<InventoryBalance[]>("/inventory"),
        request<Seller[]>("/setup/sellers"),
        request<Warehouse[]>("/setup/warehouses"),
        request<Location[]>("/setup/locations"),
        request<Product[]>("/setup/products"),
        request<Receipt[]>("/inbound-receipts"),
        request<Order[]>("/orders"),
        request<Shipment[]>("/shipments"),
        session.user.role === "user" || session.user.role === "staff"
          ? Promise.resolve([])
          : request<Invoice[]>("/invoices"),
        session.user.role === "user" || session.user.role === "staff"
          ? Promise.resolve([])
          : request<Payment[]>("/payments"),
      ]);
      setBalances(inventory);
      setSellers(sellerList);
      setWarehouses(warehouseList);
      setLocations(locationList);
      setProducts(productList);
      setReceipts(receiptList);
      setOrders(orderList);
      setShipments(shipmentList);
      setInvoices(invoiceList);
      setPayments(paymentList);
      setApiState("online");
    } catch {
      setApiState("offline");
    } finally {
      setLoading(false);
    }
  }, [request, session]);

  useEffect(() => {
    const saved = localStorage.getItem("whitfield_session");
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Session;
        if (hasExpiredAccessToken(parsed.access_token)) {
          localStorage.removeItem("whitfield_session");
          setShowAuth(true);
          setIsLoading(false);
        } else {
          setSession(parsed);
          setOrganizationId(parsed.user.organization_id);
        }
      } catch {
        localStorage.removeItem("whitfield_session");
        setShowAuth(true);
        setIsLoading(false);
      }
    }
    setAuthReady(true);
  }, []);

  useEffect(() => {
    if (session) void refresh();
  }, [refresh, session]);
  useEffect(() => {
    if (!session) return;
    const timer = window.setInterval(() => void refresh(), 10000);
    return () => window.clearInterval(timer);
  }, [refresh, session]);
  useEffect(() => {
    if (!session || !organizationId) return;
    const socketUrl = `${websocketBaseUrl.replace(/^http/, "ws")}/ws/${organizationId}`;
    const socket = new WebSocket(socketUrl, [
      "whitfield-auth",
      session.access_token,
    ]);
    socket.onmessage = () => {
      void refresh();
    };
    socket.onerror = () =>
      setApiState((state) => (state === "offline" ? "offline" : "online"));
    return () => socket.close();
  }, [organizationId, refresh, session]);

  const totals = useMemo(
    () =>
      balances.reduce(
        (total, item) => ({
          ...total,
          [item.stock_status]: total[item.stock_status] + item.quantity,
        }),
        { AVAILABLE: 0, RESERVED: 0, RECEIVING: 0, DAMAGED: 0 },
      ),
    [balances],
  );
  const sellerName = (id: string) =>
    sellers.find((seller) => seller.id === id)?.name ?? "Unknown seller";
  const warehouseName = (id: string) =>
    warehouses.find((warehouse) => warehouse.id === id)?.name ??
    "Unknown warehouse";
  const productName = (id: string) =>
    products.find((product) => product.id === id)?.name ?? id.slice(0, 8);
  const locationName = (id: string) =>
    locations.find((location) => location.id === id)?.code ?? id.slice(0, 8);
  const showSuccess = (text: string) => setNotice({ type: "success", text });
  const showError = (error: unknown) =>
    setNotice({ type: "error", text: readableError(error) });

  async function postSetup(path: string, body: object, label: string) {
    try {
      const created = await request<{ id: string }>(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      showSuccess(`${label} created successfully.`);
      await refresh();
      return created;
    } catch (error) {
      showError(error);
      return null;
    }
  }

  const page =
    activeNav === "Overview" ? (
      <Overview
        userName={session?.user.name ?? "Operator"}
        totals={totals}
        balances={balances}
        orders={orders}
        receipts={receipts}
        apiState={apiState}
        onCreateOrder={() => setActiveNav("Orders")}
        sellerName={sellerName}
        warehouseName={warehouseName}
      />
    ) : activeNav === "Orders" ? (
      <OrdersPage
        sellers={sellers}
        warehouses={warehouses}
        locations={locations}
        products={products}
        orders={orders}
        sellerName={sellerName}
        warehouseName={warehouseName}
        onCreate={async (body) => {
          try {
            await request(
              "/orders",
              { method: "POST", body: JSON.stringify(body) },
              true,
            );
            showSuccess("Order created and inventory reserved.");
            await refresh();
            return true;
          } catch (error) {
            showError(error);
            return false;
          }
        }}
      />
    ) : activeNav === "Receiving" ? (
      <ReceivingPage
        sellers={sellers}
        warehouses={warehouses}
        products={products}
        locations={locations}
        receipts={receipts}
        sellerName={sellerName}
        warehouseName={warehouseName}
        onCreateReceipt={async (body) => {
          try {
            const receipt = await request<Receipt>("/inbound-receipts", {
              method: "POST",
              body: JSON.stringify(body),
            });
            showSuccess(
              `Receipt ${receipt.reference_value} is ready for scanning.`,
            );
            await refresh();
            return receipt.id;
          } catch (error) {
            showError(error);
            return null;
          }
        }}
        onScan={async (receiptId, body) => {
          try {
            await request(
              `/inbound-receipts/${receiptId}/scan`,
              { method: "POST", body: JSON.stringify(body) },
              true,
            );
            showSuccess("Stock scan recorded in the ledger.");
            await refresh();
            return true;
          } catch (error) {
            showError(error);
            return false;
          }
        }}
        onComplete={async (receiptId) => {
          try {
            await request(
              `/inbound-receipts/${receiptId}/complete`,
              { method: "POST", body: "{}" },
              true,
            );
            showSuccess("Receipt completed. Good stock is now available.");
            await refresh();
          } catch (error) {
            showError(error);
          }
        }}
      />
    ) : activeNav === "Inventory" ? (
      <InventoryPage
        balances={balances}
        sellerName={sellerName}
        warehouseName={warehouseName}
        productName={productName}
        locationName={locationName}
        loading={loading}
      />
    ) : activeNav === "Shipping" ? (
      <ShippingPage
        orders={orders}
        shipments={shipments}
        sellerName={sellerName}
        warehouseName={warehouseName}
        onRequest={request}
        onRefresh={refresh}
        showError={showError}
        showSuccess={showSuccess}
      />
    ) : activeNav === "Billing" ? (
      <BillingPage
        orders={orders}
        invoices={invoices}
        payments={payments}
        sellerName={sellerName}
        warehouseName={warehouseName}
        onRequest={request}
        onRefresh={refresh}
        showError={showError}
        showSuccess={showSuccess}
      />
    ) : activeNav === "Users" ? (
      <UsersPage
        users={users}
        onLoad={async () => {
          try {
            setUsers(await request<AppUser[]>("/auth/users"));
          } catch (error) {
            showError(error);
          }
        }}
        onRequest={request}
        showError={showError}
      />
    ) : (
      <SetupPage
        organizationId={organizationId}
        sellers={sellers}
        warehouses={warehouses}
        locations={locations}
        products={products}
        onCreate={postSetup}
      />
    );

  const followPointer = (event: MouseEvent<HTMLElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty(
      "--pointer-x",
      `${((event.clientX - bounds.left) / bounds.width) * 100}%`,
    );
    event.currentTarget.style.setProperty(
      "--pointer-y",
      `${((event.clientY - bounds.top) / bounds.height) * 100}%`,
    );
  };

  const enterDashboard = useCallback(() => {
    if (session) setIsLoading(false);
    else setShowAuth(true);
  }, [session]);
  const acceptSession = (next: Session) => {
    localStorage.setItem("whitfield_session", JSON.stringify(next));
    setSession(next);
    setOrganizationId(next.user.organization_id);
    setShowAuth(false);
    setIsLoading(false);
  };
  if (!authReady)
    return (
      <main className="auth-shell">
        <p>Loading secure workspace…</p>
      </main>
    );
  if (showAuth)
    return (
      <AuthScreen
        onAuthenticated={acceptSession}
        onBack={() => setShowAuth(false)}
      />
    );
  if (isLoading) return <LandingPage onEnter={enterDashboard} />;
  if (!session)
    return (
      <AuthScreen
        onAuthenticated={acceptSession}
        onBack={() => setIsLoading(true)}
      />
    );

  return (
    <main className="app-shell" onMouseMove={followPointer}>
      <div className="ambient ambient-one" aria-hidden="true" />
      <div className="ambient ambient-two" aria-hidden="true" />
      <div className="ambient-grid" aria-hidden="true" />
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">W</span>
          <span>Whitfield</span>
        </div>
        <div className="workspace">
          <span className="workspace-avatar">WF</span>
          <div>
            <strong>Whitfield Fulfillment</strong>
            <small>3PL Operations</small>
          </div>
          <span className="chevron">⌄</span>
        </div>
        <nav>
          <p className="nav-label">WORKSPACE</p>
          {navigation
            .filter(([label]) => {
              if (label === "Users") return session.user.role === "admin";
              if (label === "Billing")
                return (
                  session.user.role === "manager" ||
                  session.user.role === "admin"
                );
              if (label === "Setup")
                return (
                  session.user.role === "manager" ||
                  session.user.role === "admin"
                );
              return true;
            })
            .map(([label, icon]) => (
              <button
                className={`nav-item ${activeNav === label ? "active" : ""}`}
                key={label}
                onClick={() => setActiveNav(label)}
              >
                <Icon name={icon} />
                <span>{label}</span>
                {label === "Orders" && orders.length > 0 && (
                  <b>{orders.length}</b>
                )}
              </button>
            ))}
        </nav>
        <div className="sidebar-bottom">
          <button
            className="nav-item ai-nav"
            onClick={() => setAssistantOpen(true)}
          >
            <span className="ai-nav-mark">AI</span>
            <span>Operations Copilot</span>
          </button>
          <button className="nav-item">
            <span className="help-icon">?</span>
            <span>Help center</span>
          </button>
          <div className="profile">
            <span className="avatar">
              {session.user.name
                .split(" ")
                .map((part) => part[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </span>
            <div>
              <strong>{session.user.name}</strong>
              <small>{session.user.role}</small>
            </div>
            <button
              className="profile-logout"
              onClick={() => {
                localStorage.removeItem("whitfield_session");
                setSession(null);
                setIsLoading(true);
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </aside>
      <section className="content">
        <header className="topbar">
          <div className="mobile-brand">
            <span className="brand-mark">W</span>
          </div>
          <label className="search">
            <span>⌕</span>
            <input placeholder="Search orders, SKUs, locations..." />
            <kbd>⌘ K</kbd>
          </label>
          <div className="top-actions">
            <button
              className="icon-button"
              onClick={() => setAssistantOpen(true)}
              title="Open AI copilot"
            >
              ✦
            </button>
            <button
              className="icon-button"
              onClick={() => void refresh()}
              title="Refresh dashboard"
            >
              ↻
            </button>
            <div className={`connection ${apiState}`}>
              {apiState === "online"
                ? "Live"
                : apiState === "offline"
                  ? "Offline"
                  : "Connecting"}
            </div>
          </div>
        </header>
        <div className="page-content">
          {notice && (
            <div className={`notice ${notice.type}`}>
              <span>{notice.type === "success" ? "✓" : "!"}</span>
              {notice.text}
              <button onClick={() => setNotice(null)}>×</button>
            </div>
          )}
          {page}
        </div>
      </section>
      <button
        className="ai-launcher"
        onClick={() => setAssistantOpen(true)}
        aria-label="Open operations copilot"
      >
        <span>✦</span>
        <b>Ask Whitfield</b>
      </button>
      {assistantOpen && (
        <AssistantPanel
          organizationId={organizationId}
          userName={session.user.name}
          accessToken={session.access_token}
          onClose={() => setAssistantOpen(false)}
          onNavigate={(target) => setActiveNav(target)}
          onRefresh={refresh}
        />
      )}
    </main>
  );
}

function RoadLoading({ onComplete }: { onComplete: () => void }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const startedAt = performance.now();
    const duration = 3600;
    let animationFrame = 0;
    // requestAnimationFrame is intentionally used for the visual progress, but
    // browsers may throttle it while a tab is in the background. The timer
    // keeps the product handoff reliable in either case.
    const handoffTimer = window.setTimeout(onComplete, 4000);
    const animate = (now: number) => {
      const nextProgress = Math.min(((now - startedAt) / duration) * 100, 100);
      setProgress(nextProgress);
      if (nextProgress < 100) animationFrame = requestAnimationFrame(animate);
      else window.setTimeout(onComplete, 260);
    };
    animationFrame = requestAnimationFrame(animate);
    return () => {
      cancelAnimationFrame(animationFrame);
      window.clearTimeout(handoffTimer);
    };
  }, [onComplete]);

  return (
    <main
      className="road-loader"
      aria-label="Loading Whitfield warehouse operations"
    >
      <div className="road-loader-top">
        <div className="road-loader-brand">
          <span>W</span> Whitfield
        </div>
        <button onClick={onComplete}>Skip intro</button>
      </div>
      <div className="road-loader-sky">
        <i />
        <i />
        <i />
      </div>
      <section className="road-loader-content">
        <p>WHITFIELD WAREHOUSE NETWORK</p>
        <h1>
          Moving your
          <br />
          <span>operation</span> forward.
        </h1>
        <div className="road-loader-status">
          <span>CONNECTING LIVE OPERATIONS</span>
          <strong>{Math.round(progress)}%</strong>
        </div>
        <div className="road-loader-progress">
          <i style={{ width: `${progress}%` }} />
        </div>
      </section>
      <div className="road-loader-horizon">
        <span className="city city-left" />
        <span className="city city-right" />
        <span className="mountain mountain-left" />
        <span className="mountain mountain-right" />
      </div>
      <div className="road-loader-highway">
        <i className="road-edge edge-left" />
        <i className="road-edge edge-right" />
        <i className="lane lane-one" />
        <i className="lane lane-two" />
        <i className="lane lane-three" />
        <div className="road-loader-truck">
          <div className="truck-trailer">
            <span>WHITFIELD</span>
            <i />
          </div>
          <div className="truck-cab">
            <i />
            <b />
          </div>
          <span className="truck-wheel wheel-one" />
          <span className="truck-wheel wheel-two" />
          <span className="truck-wheel wheel-three" />
        </div>
      </div>
      <p className="road-loader-footer">
        INVENTORY · ORDERS · RECEIVING · FULFILLMENT
      </p>
    </main>
  );
}

function LandingPage({ onEnter }: { onEnter: () => void }) {
  const [departing, setDeparting] = useState(false);
  const launch = useCallback(() => {
    if (departing) return;
    setDeparting(true);
    window.setTimeout(onEnter, 620);
  }, [departing, onEnter]);

  useEffect(() => {
    const root = document.querySelector<HTMLElement>(".wf-site");
    if (!root) return;
    let frame = 0;
    const updateScene = () => {
      frame = 0;
      const sceneProgress = Math.min(
        Math.max(window.scrollY / (window.innerHeight * 1.45), 0),
        1,
      );
      const pageProgress = Math.min(
        window.scrollY /
          Math.max(
            document.documentElement.scrollHeight - window.innerHeight,
            1,
          ),
        1,
      );
      root.style.setProperty("--scene", sceneProgress.toFixed(3));
      root.style.setProperty("--page-progress", pageProgress.toFixed(3));
    };
    const onScroll = () => {
      if (!frame) frame = window.requestAnimationFrame(updateScene);
    };
    updateScene();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, []);

  const scrollTo = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  const tiltScene = (event: MouseEvent<HTMLElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty(
      "--mx",
      `${((event.clientX - bounds.left) / bounds.width - 0.5) * 18}px`,
    );
    event.currentTarget.style.setProperty(
      "--my",
      `${((event.clientY - bounds.top) / bounds.height - 0.5) * 12}px`,
    );
  };
  return (
    <main
      className={`wf-site${departing ? " landing-departing" : ""}`}
      onMouseMove={tiltScene}
    >
      <div className="wf-progress" aria-hidden="true">
        <i />
      </div>
      <nav className="wf-nav">
        <button
          className="wf-brand"
          onClick={() => scrollTo("top")}
          aria-label="Whitfield home"
        >
          <span>W</span>
          <b>WHITFIELD</b>
        </button>
        <div className="wf-nav-links">
          <button onClick={() => scrollTo("platform")}>Platform</button>
          <button onClick={() => scrollTo("network")}>Network</button>
          <button onClick={() => scrollTo("workflow")}>How it works</button>
        </div>
        <button className="wf-overview" onClick={launch}>
          Login / Sign up <span>↗</span>
        </button>
      </nav>

      <section className="wf-hero" id="top">
        <div className="wf-hero-stage">
          <div className="wf-glow" aria-hidden="true" />
          <div className="wf-hero-copy">
            <p className="wf-kicker">
              <i /> AI-POWERED 3PL OPERATIONS
            </p>
            <h1 style={{ color: "#fff", lineHeight: 0.92 }}>
              Supply chain
              <br />
              <em>intelligence</em>
              <br />
              in motion.
            </h1>
            <p className="wf-hero-lead">
              One real-time operating system for inventory, receiving, orders,
              fulfillment, and every warehouse in your network.
            </p>
            <div className="wf-hero-actions">
              <button
                className="wf-primary"
                onClick={() => scrollTo("platform")}
              >
                Explore the platform <span>↓</span>
              </button>
              <button className="wf-text-button" onClick={launch}>
                Open live overview <span>↗</span>
              </button>
            </div>
          </div>
          <p className="wf-scroll-note">
            <span>SCROLL TO MOVE</span>
            <i />
            <b>01 / 05</b>
          </p>
          <div
            className="wf-road-scene"
            aria-label="A Whitfield freight truck moving through a connected logistics network"
          >
            <div className="wf-sky-grid" />
            <div className="wf-orbit orbit-one" />
            <div className="wf-orbit orbit-two" />
            <div className="wf-city">
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
            </div>
            <div className="wf-data-card card-orders">
              <small>ORDER PIPELINE</small>
              <strong>CONNECTED</strong>
              <span>LIVE API</span>
            </div>
            <div className="wf-data-card card-stock">
              <small>INVENTORY LEDGER</small>
              <strong>ATOMIC</strong>
              <span>AUDITABLE</span>
            </div>
            <div className="wf-data-card card-scan">
              <small>SCAN CHANNELS</small>
              <strong>PHONE + SCANNER</strong>
              <span>READY</span>
            </div>
            <div className="wf-highway">
              <i className="wf-lane lane-a" />
              <i className="wf-lane lane-b" />
              <i className="wf-lane lane-c" />
            </div>
            <div className="wf-truck">
              <div className="wf-trailer">
                <span>WHITFIELD</span>
                <small>CONNECTED FULFILLMENT</small>
              </div>
              <div className="wf-cab">
                <i />
              </div>
              <b className="wf-wheel w1" />
              <b className="wf-wheel w2" />
              <b className="wf-wheel w3" />
            </div>
          </div>
        </div>
      </section>

      <section className="wf-intro" id="platform">
        <div className="wf-section-label">
          <span>01</span>
          <p>THE OPERATING LAYER</p>
        </div>
        <div className="wf-intro-grid">
          <h2>
            Every movement.
            <br />
            One source
            <br />
            of truth.
          </h2>
          <div>
            <p>
              Whitfield connects warehouse execution with an AI-ready control
              layer. Every scan creates a traceable event, every order reserves
              inventory safely, and every operator sees the same live state.
            </p>
            <button className="wf-inline" onClick={() => scrollTo("network")}>
              See the network <span>↘</span>
            </button>
          </div>
        </div>
        <div className="wf-capabilities">
          <article>
            <b>01</b>
            <h3>Receive</h3>
            <p>
              Barcode-first inbound workflows turn physical stock into accurate
              digital inventory.
            </p>
            <span>INBOUND →</span>
          </article>
          <article>
            <b>02</b>
            <h3>Orchestrate</h3>
            <p>
              Atomic reservations protect every seller and warehouse from
              overselling.
            </p>
            <span>INVENTORY →</span>
          </article>
          <article>
            <b>03</b>
            <h3>Fulfill</h3>
            <p>
              Orders, shipments, invoices, and operational events move as one
              workflow.
            </p>
            <span>OUTBOUND →</span>
          </article>
        </div>
      </section>

      <section
        className="wf-metrics"
        aria-label="Warehouse performance metrics"
      >
        <div>
          <strong>REAL TIME</strong>
          <span>Operational events</span>
        </div>
        <div>
          <strong>AUDITABLE</strong>
          <span>Inventory movements</span>
        </div>
        <div>
          <strong>ROLE SAFE</strong>
          <span>Protected workflows</span>
        </div>
        <div>
          <strong>1</strong>
          <span>Network source of truth</span>
        </div>
      </section>

      <section className="wf-network" id="network">
        <div className="wf-network-copy">
          <div className="wf-section-label light">
            <span>02</span>
            <p>CONNECTED NETWORK</p>
          </div>
          <h2>
            See the whole
            <br />
            operation.
            <br />
            <em>Live.</em>
          </h2>
          <p>
            Multi-seller inventory, receiving, orders, and fulfillment across
            every warehouse—updated by scanners, phones, APIs, and operators in
            real time.
          </p>
          <ul>
            <li>
              <span>01</span>Multi-warehouse inventory truth
            </li>
            <li>
              <span>02</span>Real-time scan and order events
            </li>
            <li>
              <span>03</span>Seller-level operational isolation
            </li>
          </ul>
        </div>
        <div className="wf-network-visual">
          <div className="wf-map-grid" />
          <i className="wf-route r1" />
          <i className="wf-route r2" />
          <i className="wf-route r3" />
          <div className="wf-hub">
            <span>W</span>
            <b>
              CONTROL
              <br />
              TOWER
            </b>
          </div>
          <div className="wf-node n1">
            <i />
            RENO<small>LIVE</small>
          </div>
          <div className="wf-node n2">
            <i />
            DALLAS<small>LIVE</small>
          </div>
          <div className="wf-node n3">
            <i />
            INDY<small>LIVE</small>
          </div>
          <div className="wf-pulse p1" />
          <div className="wf-pulse p2" />
        </div>
      </section>

      <section className="wf-workflow" id="workflow">
        <div className="wf-section-label">
          <span>03</span>
          <p>HOW IT MOVES</p>
        </div>
        <div className="wf-workflow-heading">
          <h2>
            From dock
            <br />
            to doorstep.
          </h2>
          <p>
            Physical movement and digital truth stay synchronized through one
            auditable workflow.
          </p>
        </div>
        <div className="wf-steps">
          <article>
            <span>01</span>
            <div className="wf-step-icon">⌁</div>
            <h3>Scan the unit</h3>
            <p>
              Phone, handheld scanner, PDF, voice, or connected channel captures
              the event.
            </p>
          </article>
          <article>
            <span>02</span>
            <div className="wf-step-icon">◎</div>
            <h3>Update the ledger</h3>
            <p>
              The inventory movement is validated, recorded, and broadcast in
              real time.
            </p>
          </article>
          <article>
            <span>03</span>
            <div className="wf-step-icon">↗</div>
            <h3>Move the order</h3>
            <p>
              Stock is reserved, fulfilled, shipped, and documented without
              duplicate work.
            </p>
          </article>
        </div>
      </section>

      <section className="wf-final">
        <p>WHITFIELD CONTROL TOWER</p>
        <h2>
          Your operation
          <br />
          is already moving.
        </h2>
        <div>
          <span>Now see it clearly.</span>
          <button onClick={launch}>
            Open secure workspace <b>↗</b>
          </button>
        </div>
      </section>
      <footer className="wf-footer">
        <button
          className="wf-brand footer-brand"
          onClick={() => scrollTo("top")}
        >
          <span>W</span>
          <b>WHITFIELD</b>
        </button>
        <p>
          Warehouse intelligence,
          <br />
          made operational.
        </p>
        <div>
          <button onClick={() => scrollTo("platform")}>Platform</button>
          <button onClick={() => scrollTo("network")}>Network</button>
          <button onClick={() => scrollTo("workflow")}>Workflow</button>
        </div>
        <small>© 2026 WHITFIELD WMS</small>
      </footer>
    </main>
  );
}

function Overview({
  userName,
  totals,
  balances,
  orders,
  receipts,
  apiState,
  onCreateOrder,
  sellerName,
  warehouseName,
}: {
  userName: string;
  totals: Record<StockStatus, number>;
  balances: InventoryBalance[];
  orders: Order[];
  receipts: Receipt[];
  apiState: string;
  onCreateOrder: () => void;
  sellerName: (id: string) => string;
  warehouseName: (id: string) => string;
}) {
  const total =
    totals.AVAILABLE + totals.RESERVED + totals.RECEIVING + totals.DAMAGED;
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">OPERATIONS OVERVIEW</p>
          <h1>
            Good morning, {userName.split(" ")[0]} <span>✦</span>
          </h1>
          <p className="subhead">
            Live warehouse activity for Whitfield Fulfillment.
          </p>
        </div>
        <div className="heading-actions">
          <button className="secondary-button">Export report</button>
          <button className="primary-button" onClick={onCreateOrder}>
            ＋ Create order
          </button>
        </div>
      </div>
      <section className="stats-grid">
        <Stat
          icon="▣"
          tone="blue"
          label="Total inventory"
          value={total.toLocaleString()}
          detail="units across all locations"
        />
        <Stat
          icon="□"
          tone="purple"
          label="Orders to fulfill"
          value={String(
            orders.filter((order) => order.status === "RESERVED").length,
          )}
          detail="inventory reserved safely"
        />
        <Stat
          icon="◫"
          tone="orange"
          label="Open receipts"
          value={String(
            receipts.filter((receipt) => receipt.status === "DRAFT").length,
          )}
          detail={`${totals.RECEIVING} units awaiting completion`}
        />
        <Stat
          icon="✓"
          tone="green"
          label="Available stock"
          value={totals.AVAILABLE.toLocaleString()}
          detail="ready for new orders"
        />
      </section>
      <section className="dashboard-grid">
        <article className="panel orders-panel">
          <div className="panel-heading">
            <div>
              <h2>Recent fulfillment orders</h2>
              <p>Reservations made through the live API</p>
            </div>
            <button className="text-button" onClick={onCreateOrder}>
              Create order →
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ORDER</th>
                  <th>SELLER</th>
                  <th>WAREHOUSE</th>
                  <th>STATUS</th>
                </tr>
              </thead>
              <tbody>
                {orders.length ? (
                  orders.slice(0, 5).map((order) => (
                    <tr key={order.id}>
                      <td>
                        <strong>#{order.order_number}</strong>
                        <small>
                          {order.item_count} item
                          {order.item_count === 1 ? "" : "s"} · {order.source}
                        </small>
                      </td>
                      <td>{sellerName(order.seller_id)}</td>
                      <td>{warehouseName(order.warehouse_id)}</td>
                      <td>
                        <StatusPill
                          label={
                            order.status === "RESERVED"
                              ? "Reserved"
                              : order.status
                          }
                          tone="blue"
                        />
                      </td>
                    </tr>
                  ))
                ) : (
                  <EmptyRow
                    columns={4}
                    text="No orders yet. Create one to reserve inventory."
                  />
                )}
              </tbody>
            </table>
          </div>
        </article>
        <article className="panel capacity-panel">
          <div className="panel-heading">
            <div>
              <h2>Inventory health</h2>
              <p>Current ledger balances</p>
            </div>
            <span className={`api-badge ${apiState}`}>
              ● {apiState === "online" ? "Live data" : "Connecting"}
            </span>
          </div>
          <div className="inventory-health vertical">
            <HealthLine
              color="available"
              label="Available"
              value={totals.AVAILABLE}
            />
            <HealthLine
              color="reserved"
              label="Reserved"
              value={totals.RESERVED}
            />
            <HealthLine
              color="receiving"
              label="Receiving"
              value={totals.RECEIVING}
            />
            <HealthLine
              color="damaged"
              label="Damaged"
              value={totals.DAMAGED}
            />
          </div>
          <div className="health-bar">
            <i
              style={{
                width: `${total ? Math.max(4, (totals.AVAILABLE / total) * 100) : 0}%`,
              }}
            />
          </div>
          <p className="small-note">
            Every balance is derived from auditable inventory movements.
          </p>
        </article>
        <article className="panel activity-panel">
          <div className="panel-heading">
            <div>
              <h2>Receiving activity</h2>
              <p>
                Inbound stock becomes sellable only after receipt completion.
              </p>
            </div>
          </div>
          <div className="activity">
            {receipts.slice(0, 3).map((receipt) => (
              <div key={receipt.id}>
                <span
                  className={`activity-icon ${receipt.status === "COMPLETED" ? "receive" : "alert"}`}
                >
                  {receipt.status === "COMPLETED" ? "↓" : "!"}
                </span>
                <p>
                  <strong>{receipt.reference_value}</strong>
                  <small>
                    {sellerName(receipt.seller_id)} ·{" "}
                    {warehouseName(receipt.warehouse_id)} · {receipt.line_count}{" "}
                    scan
                    {receipt.line_count === 1 ? "" : "s"}
                  </small>
                </p>
                <time>{receipt.status}</time>
              </div>
            ))}
            {!receipts.length && (
              <p className="empty-copy">No inbound receipts yet.</p>
            )}
          </div>
        </article>
      </section>
    </>
  );
}

function Stat({
  icon,
  tone,
  label,
  value,
  detail,
}: {
  icon: string;
  tone: string;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <article className="stat-card">
      <div className="stat-top">
        <span className={`stat-icon ${tone}`}>{icon}</span>
        <span className="trend positive">Live</span>
      </div>
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}
function HealthLine({
  color,
  label,
  value,
}: {
  color: string;
  label: string;
  value: number;
}) {
  return (
    <div>
      <span className={`legend ${color}`} />
      {label}
      <strong>{value}</strong>
    </div>
  );
}
function EmptyRow({ columns, text }: { columns: number; text: string }) {
  return (
    <tr>
      <td colSpan={columns} className="empty-cell">
        {text}
      </td>
    </tr>
  );
}

function OrdersPage({
  sellers,
  warehouses,
  locations,
  products,
  orders,
  sellerName,
  warehouseName,
  onCreate,
}: {
  sellers: Seller[];
  warehouses: Warehouse[];
  locations: Location[];
  products: Product[];
  orders: Order[];
  sellerName: (id: string) => string;
  warehouseName: (id: string) => string;
  onCreate: (body: object) => Promise<boolean>;
}) {
  const [sellerId, setSellerId] = useState(sellers[0]?.id ?? "");
  const [warehouseId, setWarehouseId] = useState(warehouses[0]?.id ?? "");
  const [productId, setProductId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [orderNumber, setOrderNumber] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (!sellerId && sellers[0]) setSellerId(sellers[0].id);
    if (!warehouseId && warehouses[0]) setWarehouseId(warehouses[0].id);
  }, [sellerId, warehouseId, sellers, warehouses]);
  useEffect(() => {
    if (!orderNumber) setOrderNumber(createOrderNumber());
  }, [orderNumber]);
  const filteredProducts = products.filter(
    (product) => product.seller_id === sellerId,
  );
  const filteredLocations = locations.filter(
    (location) => location.warehouse_id === warehouseId,
  );
  useEffect(() => {
    setProductId(filteredProducts[0]?.id ?? "");
  }, [sellerId, products.length]);
  useEffect(() => {
    setLocationId(filteredLocations[0]?.id ?? "");
  }, [warehouseId, locations.length]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    const created = await onCreate({
      seller_id: sellerId,
      warehouse_id: warehouseId,
      order_number: orderNumber.trim(),
      source: "MANUAL",
      items: [
        {
          product_id: productId,
          location_id: locationId,
          quantity: Number(form.get("quantity")),
        },
      ],
    });
    if (created) setOrderNumber(createOrderNumber());
    setSaving(false);
  }
  return (
    <>
      <PageTitle
        eyebrow="FULFILLMENT"
        title="Orders"
        description="Create an order and reserve stock atomically before picking."
      />
      <div className="workflow-grid">
        <FormCard
          title="Create manual order"
          subtitle="Stock is reserved immediately if enough is available."
        >
          <form onSubmit={submit} className="form-grid">
            <Input
              name="order_number"
              label="Order number"
              value={orderNumber}
              onChange={(event) => setOrderNumber(event.target.value)}
              required
            />
            <Select
              label="Seller"
              value={sellerId}
              onChange={setSellerId}
              options={sellers.map((item) => [
                item.id,
                `${item.name} · ${item.code}`,
              ])}
            />
            <Select
              label="Warehouse"
              value={warehouseId}
              onChange={setWarehouseId}
              options={warehouses.map((item) => [
                item.id,
                `${item.name} · ${item.code}`,
              ])}
            />
            <Select
              label="Product / SKU"
              value={productId}
              onChange={setProductId}
              options={filteredProducts.map((item) => [
                item.id,
                `${item.name} · ${item.sku} · ${item.barcode}`,
              ])}
            />
            <Select
              label="Pick location"
              value={locationId}
              onChange={setLocationId}
              options={filteredLocations.map((item) => [
                item.id,
                `${item.code} — ${item.name}`,
              ])}
            />
            <Input
              name="quantity"
              label="Quantity"
              type="number"
              min="1"
              defaultValue="1"
              required
            />
            <button
              className="primary-button full"
              disabled={
                saving || !orderNumber.trim() || !productId || !locationId
              }
            >
              {saving ? "Reserving..." : "Reserve inventory & create order"}
            </button>
          </form>
        </FormCard>
        <article className="panel callout">
          <span className="callout-icon">✓</span>
          <h2>Overselling prevention</h2>
          <p>
            The backend uses an atomic transaction. If another order already
            reserved the last units, this request returns an error instead of
            creating a bad order.
          </p>
        </article>
      </div>
      <DataTable title="All orders" subtitle="Live records from the WMS API">
        <table>
          <thead>
            <tr>
              <th>ORDER</th>
              <th>SELLER</th>
              <th>WAREHOUSE</th>
              <th>ITEMS</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id}>
                <td>
                  <strong>#{order.order_number}</strong>
                  <small>{order.source}</small>
                </td>
                <td>{sellerName(order.seller_id)}</td>
                <td>{warehouseName(order.warehouse_id)}</td>
                <td>{order.item_count}</td>
                <td>
                  <StatusPill label={order.status} />
                </td>
              </tr>
            ))}
            {!orders.length && (
              <EmptyRow columns={5} text="No orders have been created." />
            )}
          </tbody>
        </table>
      </DataTable>
    </>
  );
}

function ReceivingPage({
  sellers,
  warehouses,
  products,
  locations,
  receipts,
  sellerName,
  warehouseName,
  onCreateReceipt,
  onScan,
  onComplete,
}: {
  sellers: Seller[];
  warehouses: Warehouse[];
  products: Product[];
  locations: Location[];
  receipts: Receipt[];
  sellerName: (id: string) => string;
  warehouseName: (id: string) => string;
  onCreateReceipt: (body: object) => Promise<string | null>;
  onScan: (id: string, body: object) => Promise<boolean>;
  onComplete: (id: string) => Promise<void>;
}) {
  const [sellerId, setSellerId] = useState(sellers[0]?.id ?? "");
  const [warehouseId, setWarehouseId] = useState(warehouses[0]?.id ?? "");
  const [receiptId, setReceiptId] = useState("");
  const [productId, setProductId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [referenceType, setReferenceType] = useState("MANUAL_TICKET");
  const [condition, setCondition] = useState("GOOD");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!sellerId && sellers[0]) setSellerId(sellers[0].id);
    if (!warehouseId && warehouses[0]) setWarehouseId(warehouses[0].id);
  }, [sellerId, warehouseId, sellers, warehouses]);
  const productsForSeller = products.filter(
    (product) => product.seller_id === sellerId,
  );
  const locationsForWarehouse = locations.filter(
    (location) => location.warehouse_id === warehouseId,
  );
  const draftReceipts = receipts.filter(
    (receipt) => receipt.status === "DRAFT",
  );
  useEffect(() => {
    setProductId(productsForSeller[0]?.id ?? "");
  }, [sellerId, products.length]);
  useEffect(() => {
    setLocationId(locationsForWarehouse[0]?.id ?? "");
  }, [warehouseId, locations.length]);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    const id = await onCreateReceipt({
      seller_id: sellerId,
      warehouse_id: warehouseId,
      reference_type: referenceType,
      reference_value: String(data.get("reference_value")).trim(),
    });
    if (id) setReceiptId(id);
    setBusy(false);
  }
  async function scan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (!receiptId) return;
    setBusy(true);
    await onScan(receiptId, {
      product_id: productId,
      location_id: locationId,
      quantity: Number(data.get("quantity")),
      condition,
    });
    setBusy(false);
  }
  return (
    <>
      <PageTitle
        eyebrow="INBOUND OPERATIONS"
        title="Receiving"
        description="Scan stock into receiving, then complete the receipt to release good units as available."
      />
      <div className="receiving-grid">
        <FormCard
          title="1. Open inbound receipt"
          subtitle="Carrier tracking or an in-person ticket prevents duplicate receipts."
        >
          <form onSubmit={create} className="form-grid">
            <Select
              label="Seller"
              value={sellerId}
              onChange={setSellerId}
              options={sellers.map((item) => [
                item.id,
                `${item.name} · ${item.code}`,
              ])}
            />
            <Select
              label="Warehouse"
              value={warehouseId}
              onChange={setWarehouseId}
              options={warehouses.map((item) => [
                item.id,
                `${item.name} · ${item.code}`,
              ])}
            />
            <Select
              label="Reference type"
              value={referenceType}
              onChange={setReferenceType}
              options={[
                ["MANUAL_TICKET", "Manual ticket"],
                ["CARRIER_TRACKING", "Carrier tracking"],
              ]}
            />
            <Input
              name="reference_value"
              label="Reference number"
              placeholder="e.g. TICKET-204"
              required
            />
            <button className="primary-button full" disabled={busy}>
              Create receipt
            </button>
          </form>
        </FormCard>
        <FormCard
          title="2. Scan product"
          subtitle="Good units remain in RECEIVING until the receipt is completed."
        >
          <form onSubmit={scan} className="form-grid">
            <Select
              label="Active receipt"
              value={receiptId}
              onChange={setReceiptId}
              options={[
                ["", "Select a draft receipt"],
                ...draftReceipts.map((item) => [
                  item.id,
                  `${item.reference_value} (${item.line_count} scans)`,
                ]),
              ]}
            />
            <Select
              label="Product / barcode"
              value={productId}
              onChange={setProductId}
              options={productsForSeller.map((item) => [
                item.id,
                `${item.name} · ${item.sku} · ${item.barcode}`,
              ])}
            />
            <Select
              label="Putaway location"
              value={locationId}
              onChange={setLocationId}
              options={locationsForWarehouse.map((item) => [
                item.id,
                `${item.code} — ${item.name}`,
              ])}
            />
            <Input
              name="quantity"
              label="Scanned quantity"
              type="number"
              min="1"
              defaultValue="1"
              required
            />
            <Select
              label="Condition"
              value={condition}
              onChange={setCondition}
              options={[
                ["GOOD", "Good — sellable after completion"],
                ["DAMAGED", "Damaged — non-sellable"],
              ]}
            />
            <button
              className="secondary-button full"
              disabled={busy || !receiptId || !productId || !locationId}
            >
              {busy ? "Saving..." : "Record scan"}
            </button>
          </form>
          {receiptId && (
            <button
              className="primary-button full complete-button"
              onClick={() => void onComplete(receiptId)}
            >
              Complete receipt & release stock
            </button>
          )}
        </FormCard>
      </div>
      <DataTable
        title="Inbound receipts"
        subtitle="Every receipt is independently traceable."
      >
        <table>
          <thead>
            <tr>
              <th>REFERENCE</th>
              <th>SELLER</th>
              <th>WAREHOUSE</th>
              <th>SCANS</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {receipts.map((receipt) => (
              <tr key={receipt.id}>
                <td>
                  <strong>{receipt.reference_value}</strong>
                  <small>{receipt.reference_type.replace("_", " ")}</small>
                </td>
                <td>{sellerName(receipt.seller_id)}</td>
                <td>{warehouseName(receipt.warehouse_id)}</td>
                <td>{receipt.line_count}</td>
                <td>
                  <StatusPill
                    label={receipt.status}
                    tone={receipt.status === "COMPLETED" ? "green" : "amber"}
                  />
                </td>
              </tr>
            ))}
            {!receipts.length && (
              <EmptyRow columns={5} text="No receipts have been created." />
            )}
          </tbody>
        </table>
      </DataTable>
    </>
  );
}

function InventoryPage({
  balances,
  sellerName,
  warehouseName,
  productName,
  locationName,
  loading,
}: {
  balances: InventoryBalance[];
  sellerName: (id: string) => string;
  warehouseName: (id: string) => string;
  productName: (id: string) => string;
  locationName: (id: string) => string;
  loading: boolean;
}) {
  return (
    <>
      <PageTitle
        eyebrow="STOCK CONTROL"
        title="Inventory ledger"
        description="Current balances by seller, product, warehouse, bin, and stock state."
      />
      <DataTable
        title="Live inventory positions"
        subtitle={
          loading
            ? "Refreshing live data..."
            : `${balances.length} stock positions returned by the API.`
        }
      >
        <table>
          <thead>
            <tr>
              <th>PRODUCT</th>
              <th>SELLER</th>
              <th>WAREHOUSE</th>
              <th>LOCATION</th>
              <th>STATE</th>
              <th>QUANTITY</th>
            </tr>
          </thead>
          <tbody>
            {balances.map((balance, index) => (
              <tr
                key={`${balance.product_id}-${balance.stock_status}-${index}`}
              >
                <td>
                  <strong>{productName(balance.product_id)}</strong>
                  <small>{balance.product_id.slice(0, 8)}</small>
                </td>
                <td>{sellerName(balance.seller_id)}</td>
                <td>{warehouseName(balance.warehouse_id)}</td>
                <td>{locationName(balance.location_id)}</td>
                <td>
                  <StatusPill
                    label={balance.stock_status}
                    tone={
                      balance.stock_status === "AVAILABLE"
                        ? "green"
                        : balance.stock_status === "DAMAGED"
                          ? "amber"
                          : "blue"
                    }
                  />
                </td>
                <td>
                  <strong>{balance.quantity}</strong>
                </td>
              </tr>
            ))}
            {!balances.length && (
              <EmptyRow
                columns={6}
                text="No inventory positions yet. Receive stock to create one."
              />
            )}
          </tbody>
        </table>
      </DataTable>
    </>
  );
}

function SetupPage({
  organizationId,
  sellers,
  warehouses,
  locations,
  products,
  onCreate,
}: {
  organizationId: string;
  sellers: Seller[];
  warehouses: Warehouse[];
  locations: Location[];
  products: Product[];
  onCreate: (
    path: string,
    body: object,
    label: string,
  ) => Promise<{ id: string } | null>;
}) {
  const [sellerId, setSellerId] = useState(sellers[0]?.id ?? "");
  const [warehouseId, setWarehouseId] = useState(warehouses[0]?.id ?? "");
  useEffect(() => {
    if (!sellerId && sellers[0]) setSellerId(sellers[0].id);
    if (!warehouseId && warehouses[0]) setWarehouseId(warehouses[0].id);
  }, [sellerId, warehouseId, sellers, warehouses]);
  const submit =
    (path: string, label: string, transform: (data: FormData) => object) =>
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const created = await onCreate(
        path,
        transform(new FormData(event.currentTarget)),
        label,
      );
      if (!created) return;
      if (path === "/setup/sellers") setSellerId(created.id);
      if (path === "/setup/warehouses") setWarehouseId(created.id);
      event.currentTarget.reset();
    };
  return (
    <>
      <PageTitle
        eyebrow="SYSTEM SETUP"
        title="Warehouse master data"
        description={`Active organization: ${organizationId.slice(0, 8)}… Create sellers, locations, and SKUs before receiving inventory.`}
      />
      <div className="setup-grid">
        <FormCard
          title="Seller client"
          subtitle="Inventory stays owned by its seller."
        >
          <form
            onSubmit={submit("/setup/sellers", "Seller", (data) => ({
              name: data.get("name"),
              code: String(data.get("code")).toUpperCase(),
            }))}
            className="form-grid"
          >
            <Input
              name="name"
              label="Seller name"
              placeholder="e.g. Summit Outdoor"
              required
            />
            <Input
              name="code"
              label="Seller code"
              placeholder="SUMMIT"
              pattern="[A-Za-z0-9_-]{2,20}"
              required
            />
            <button className="primary-button full">Add seller</button>
          </form>
        </FormCard>
        <FormCard
          title="Warehouse"
          subtitle="Create a physical warehouse site."
        >
          <form
            onSubmit={submit("/setup/warehouses", "Warehouse", (data) => ({
              name: data.get("name"),
              code: String(data.get("code")).toUpperCase(),
              city: data.get("city"),
              state: data.get("state"),
            }))}
            className="form-grid"
          >
            <Input
              name="name"
              label="Warehouse name"
              placeholder="Reno Fulfillment Center"
              required
            />
            <Input
              name="code"
              label="Warehouse code"
              placeholder="RENO"
              required
            />
            <Input name="city" label="City" placeholder="Reno" required />
            <Input name="state" label="State" placeholder="Nevada" required />
            <button className="primary-button full">Add warehouse</button>
          </form>
        </FormCard>
        <FormCard
          title="Bin location"
          subtitle="A scan-ready physical location."
        >
          <form
            onSubmit={submit("/setup/locations", "Location", (data) => ({
              warehouse_id: warehouseId,
              name: data.get("name"),
              code: String(data.get("code")).toUpperCase(),
            }))}
            className="form-grid"
          >
            <Select
              label="Warehouse"
              value={warehouseId}
              onChange={setWarehouseId}
              options={warehouses.map((item) => [
                item.id,
                `${item.name} · ${item.code}`,
              ])}
            />
            <Input
              name="name"
              label="Location name"
              placeholder="Aisle A / Bin 01"
              required
            />
            <Input
              name="code"
              label="Location code"
              placeholder="A-01"
              required
            />
            <button className="primary-button full" disabled={!warehouseId}>
              Add location
            </button>
          </form>
        </FormCard>
        <FormCard
          title="Product SKU"
          subtitle="Attach a seller-owned SKU and barcode."
        >
          <form
            onSubmit={submit("/setup/products", "Product", (data) => ({
              seller_id: sellerId,
              sku: String(data.get("sku")).toUpperCase(),
              name: data.get("name"),
              barcode: data.get("barcode"),
            }))}
            className="form-grid"
          >
            <Select
              label="Seller"
              value={sellerId}
              onChange={setSellerId}
              options={sellers.map((item) => [
                item.id,
                `${item.name} · ${item.code}`,
              ])}
            />
            <Input
              name="name"
              label="Product name"
              placeholder="Rechargeable Camp Lantern"
              required
            />
            <Input
              name="sku"
              label="SKU"
              placeholder="CAMP-LANTERN-01"
              required
            />
            <Input
              name="barcode"
              label="UPC / barcode"
              placeholder="012345678905"
              required
            />
            <button className="primary-button full" disabled={!sellerId}>
              Add product
            </button>
          </form>
        </FormCard>
      </div>
      <AutomationDirectory
        organizationId={organizationId}
        sellers={sellers}
        warehouses={warehouses}
        locations={locations}
        products={products}
      />
    </>
  );
}

function AutomationDirectory({
  organizationId,
  sellers,
  warehouses,
  locations,
  products,
}: {
  organizationId: string;
  sellers: Seller[];
  warehouses: Warehouse[];
  locations: Location[];
  products: Product[];
}) {
  const sellerById = (id: string) =>
    sellers.find((item) => item.id === id)?.code ?? "Unknown seller";
  const warehouseById = (id: string) =>
    warehouses.find((item) => item.id === id)?.code ?? "Unknown warehouse";
  const rows = [
    ...sellers.map((item) => ({
      type: "SELLER",
      name: item.name,
      code: item.code,
      id: item.id,
      owner: `Organization ${organizationId.slice(0, 8)}`,
    })),
    ...warehouses.map((item) => ({
      type: "WAREHOUSE",
      name: item.name,
      code: item.code,
      id: item.id,
      owner: `${item.city}, ${item.state}`,
    })),
    ...locations.map((item) => ({
      type: "LOCATION",
      name: item.name,
      code: item.code,
      id: item.id,
      owner: `Warehouse ${warehouseById(item.warehouse_id)}`,
    })),
    ...products.map((item) => ({
      type: "PRODUCT",
      name: item.name,
      code: item.sku,
      id: item.id,
      owner: `Seller ${sellerById(item.seller_id)}`,
    })),
  ];
  return (
    <DataTable
      title="Advanced integration IDs"
      subtitle="Internal UUID mappings for APIs, imports, scanners, and automation. Warehouse operators normally use the names and business codes shown above."
    >
      <table className="automation-table">
        <thead>
          <tr>
            <th>TYPE</th>
            <th>NAME</th>
            <th>CODE / SKU</th>
            <th>UUID</th>
            <th>RELATION</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((item) => (
            <tr key={`${item.type}-${item.id}`}>
              <td>
                <StatusPill label={item.type} tone="slate" />
              </td>
              <td>
                <strong>{item.name}</strong>
              </td>
              <td>{item.code}</td>
              <td>
                <MachineId value={item.id} compact />
              </td>
              <td>{item.owner}</td>
            </tr>
          ))}
          {!rows.length && (
            <EmptyRow columns={5} text="No master-data UUIDs available yet." />
          )}
        </tbody>
      </table>
    </DataTable>
  );
}

function AuthScreen({
  onAuthenticated,
  onBack,
}: {
  onAuthenticated: (session: Session) => void;
  onBack: () => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [role, setRole] = useState("user");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const payload =
      mode === "login"
        ? { email: data.get("email"), password: data.get("password") }
        : {
            name: data.get("name"),
            email: data.get("email"),
            password: data.get("password"),
            organization_id: data.get("organization_id"),
            role,
            invite_code: data.get("invite_code") || null,
          };
    try {
      const response = await fetch(
        `${apiBaseUrl}/auth/${mode === "login" ? "login" : "register"}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      const body = await response.json().catch(() => null);
      if (!response.ok)
        throw new Error(
          typeof body?.detail === "string"
            ? body.detail
            : "Authentication failed",
        );
      onAuthenticated(body as Session);
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="auth-shell">
      <button className="auth-back" onClick={onBack}>
        ← Back
      </button>
      <section className="auth-card">
        <div className="auth-brand">
          <span>W</span>
          <div>
            <strong>Whitfield</strong>
            <small>Secure warehouse workspace</small>
          </div>
        </div>
        <h1>{mode === "login" ? "Welcome back." : "Create your account."}</h1>
        <p>One secure login for users, staff, managers and administrators.</p>
        <div className="auth-tabs">
          <button
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Login
          </button>
          <button
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Sign up
          </button>
        </div>
        {error && <div className="ai-error">{error}</div>}
        <form onSubmit={submit}>
          {mode === "register" && (
            <>
              <Input name="name" label="Full name" required />
              <Input name="organization_id" label="Organization ID" required />
              <Select
                label="Role"
                value={role}
                onChange={setRole}
                options={[
                  ["user", "User"],
                  ["staff", "Staff"],
                  ["manager", "Manager"],
                  ["admin", "Admin"],
                ]}
              />
              <Input name="invite_code" label="Manager/admin invite code" />
            </>
          )}
          <Input name="email" label="Email" type="email" required />
          <Input
            name="password"
            label="Password"
            type="password"
            minLength={10}
            required
          />
          <button className="primary-button full" disabled={busy}>
            {busy
              ? "Please wait…"
              : mode === "login"
                ? "Login securely"
                : "Create account"}
          </button>
        </form>
        <small className="auth-note">
          Manager and admin registration requires a predefined invite code. The
          first account in a new organization may become its administrator.
        </small>
      </section>
    </main>
  );
}

function ShippingPage({
  orders,
  shipments,
  sellerName,
  warehouseName,
  onRequest,
  onRefresh,
  showError,
  showSuccess,
}: {
  orders: Order[];
  shipments: Shipment[];
  sellerName: (id: string) => string;
  warehouseName: (id: string) => string;
  onRequest: ApiRequest;
  onRefresh: () => Promise<void>;
  showError: (error: unknown) => void;
  showSuccess: (text: string) => void;
}) {
  const [orderId, setOrderId] = useState(
    orders.find((item) => item.status === "RESERVED")?.id ?? "",
  );
  useEffect(() => {
    if (!orderId)
      setOrderId(orders.find((item) => item.status === "RESERVED")?.id ?? "");
  }, [orders, orderId]);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      await onRequest("/shipments", {
        method: "POST",
        body: JSON.stringify({
          order_id: orderId,
          carrier_id: data.get("carrier_id"),
          carrier_name: data.get("carrier_name"),
          service_level: data.get("service_level"),
          tracking_number: data.get("tracking_number"),
          ship_to: {
            name: data.get("name"),
            line1: data.get("line1"),
            city: data.get("city"),
            state: data.get("state"),
            postal_code: data.get("postal_code"),
            country: "US",
          },
        }),
      });
      showSuccess(
        "Shipment created and reserved stock released from the warehouse.",
      );
      await onRefresh();
    } catch (error) {
      showError(error);
    }
  };
  const update = async (id: string, status: string) => {
    try {
      await onRequest(`/shipments/${id}/events`, {
        method: "POST",
        body: JSON.stringify({ status, note: `Status changed to ${status}` }),
      });
      showSuccess("Tracking updated.");
      await onRefresh();
    } catch (error) {
      showError(error);
    }
  };
  return (
    <>
      <PageTitle
        eyebrow="OUTBOUND LOGISTICS"
        title="Shipping & tracking"
        description="Convert reserved orders into carrier-tracked shipments in one auditable transaction."
      />
      <div className="workflow-grid shipping-workflow">
        <FormCard
          title="Create shipment"
          subtitle="Carrier and destination details become the permanent tracking record."
        >
          <form className="form-grid" onSubmit={submit}>
            <Select
              label="Reserved order"
              value={orderId}
              onChange={setOrderId}
              options={orders
                .filter((item) => item.status === "RESERVED")
                .map((item) => [
                  item.id,
                  `${item.order_number} · ${sellerName(item.seller_id)} · ${warehouseName(item.warehouse_id)}`,
                ])}
            />
            <Input
              name="carrier_id"
              label="Carrier ID"
              placeholder="UPS"
              required
            />
            <Input
              name="carrier_name"
              label="Carrier name"
              placeholder="UPS"
              required
            />
            <Input
              name="service_level"
              label="Service level"
              placeholder="Ground"
              required
            />
            <Input name="tracking_number" label="Tracking number" required />
            <Input name="name" label="Recipient" required />
            <Input name="line1" label="Street address" required />
            <Input name="city" label="City" required />
            <Input name="state" label="State" required />
            <Input name="postal_code" label="ZIP code" required />
            <button className="primary-button full" disabled={!orderId}>
              Create shipment
            </button>
          </form>
        </FormCard>
      </div>
      <DataTable
        title="Shipment tracking"
        subtitle="Live carrier lifecycle records"
      >
        <table className="shipment-table">
          <thead>
            <tr>
              <th>ORDER</th>
              <th>CARRIER</th>
              <th>TRACKING</th>
              <th>DESTINATION</th>
              <th>STATUS</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {shipments.map((item) => (
              <tr key={item.id}>
                <td>#{item.order_number}</td>
                <td>
                  {item.carrier_name}
                  <small>
                    {item.carrier_id} · {item.service_level}
                  </small>
                </td>
                <td>{item.tracking_number}</td>
                <td>
                  {item.ship_to.city}, {item.ship_to.state}
                </td>
                <td>
                  <StatusPill
                    label={item.status}
                    tone={item.status === "DELIVERED" ? "green" : "blue"}
                  />
                </td>
                <td>
                  <select
                    value={item.status}
                    onChange={(event) =>
                      void update(item.id, event.target.value)
                    }
                  >
                    <option>LABEL_CREATED</option>
                    <option>PICKED_UP</option>
                    <option>IN_TRANSIT</option>
                    <option>OUT_FOR_DELIVERY</option>
                    <option>DELIVERED</option>
                    <option>EXCEPTION</option>
                  </select>
                </td>
              </tr>
            ))}
            {!shipments.length && (
              <EmptyRow columns={6} text="No shipments yet." />
            )}
          </tbody>
        </table>
      </DataTable>
    </>
  );
}

function BillingPage({
  orders,
  invoices,
  payments,
  sellerName,
  warehouseName,
  onRequest,
  onRefresh,
  showError,
  showSuccess,
}: {
  orders: Order[];
  invoices: Invoice[];
  payments: Payment[];
  sellerName: (id: string) => string;
  warehouseName: (id: string) => string;
  onRequest: ApiRequest;
  onRefresh: () => Promise<void>;
  showError: (error: unknown) => void;
  showSuccess: (text: string) => void;
}) {
  const [orderId, setOrderId] = useState(orders[0]?.id ?? "");
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      await onRequest("/invoices", {
        method: "POST",
        body: JSON.stringify({
          order_id: orderId,
          subtotal_cents: Math.round(Number(data.get("subtotal")) * 100),
          tax_cents: Math.round(Number(data.get("tax")) * 100),
          currency: "usd",
          due_days: 30,
        }),
      });
      showSuccess("Invoice created.");
      await onRefresh();
    } catch (error) {
      showError(error);
    }
  };
  const pay = async (invoiceId: string) => {
    try {
      const payment = await onRequest<Payment>(
        `/invoices/${invoiceId}/payment-intent`,
        { method: "POST", body: "{}" },
      );
      showSuccess(
        payment.provider === "stripe"
          ? "Stripe payment intent created."
          : "Payment gateway is not configured; no charge was attempted.",
      );
      await onRefresh();
    } catch (error) {
      showError(error);
    }
  };
  return (
    <>
      <PageTitle
        eyebrow="FINANCE"
        title="Invoices & payments"
        description="Invoice totals are server-controlled; gateway credentials never enter the browser."
      />
      <div className="workflow-grid">
        <FormCard
          title="Create invoice"
          subtitle="Create one invoice per fulfillment order."
        >
          <form className="form-grid" onSubmit={submit}>
            <Select
              label="Order"
              value={orderId}
              onChange={setOrderId}
              options={orders.map((item) => [
                item.id,
                `${item.order_number} · ${sellerName(item.seller_id)} · ${warehouseName(item.warehouse_id)}`,
              ])}
            />
            <Input
              name="subtotal"
              label="Subtotal (USD)"
              type="number"
              min="0.01"
              step="0.01"
              required
            />
            <Input
              name="tax"
              label="Tax (USD)"
              type="number"
              min="0"
              step="0.01"
              defaultValue="0"
              required
            />
            <button className="primary-button full" disabled={!orderId}>
              Create invoice
            </button>
          </form>
        </FormCard>
      </div>
      <DataTable
        title="Invoices"
        subtitle="Stripe PaymentIntent is created from the stored invoice total"
      >
        <table>
          <thead>
            <tr>
              <th>INVOICE</th>
              <th>ORDER</th>
              <th>TOTAL</th>
              <th>DUE</th>
              <th>STATUS</th>
              <th>PAYMENT</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((item) => {
              const payment = payments.find(
                (value) => value.invoice_id === item.id,
              );
              return (
                <tr key={item.id}>
                  <td>{item.invoice_number}</td>
                  <td>#{item.order_number}</td>
                  <td>
                    ${(item.total_cents / 100).toFixed(2)}{" "}
                    {item.currency.toUpperCase()}
                  </td>
                  <td>{new Date(item.due_at).toLocaleDateString()}</td>
                  <td>
                    <StatusPill label={item.status} />
                  </td>
                  <td>
                    {payment ? (
                      `${payment.provider}: ${payment.status}`
                    ) : (
                      <button
                        className="text-button"
                        onClick={() => void pay(item.id)}
                      >
                        Create payment intent
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
            {!invoices.length && (
              <EmptyRow columns={6} text="No invoices yet." />
            )}
          </tbody>
        </table>
      </DataTable>
    </>
  );
}

function UsersPage({
  users,
  onLoad,
  onRequest,
  showError,
}: {
  users: AppUser[];
  onLoad: () => Promise<void>;
  onRequest: ApiRequest;
  showError: (error: unknown) => void;
}) {
  useEffect(() => {
    void onLoad();
  }, []);
  const update = async (id: string, role: string) => {
    try {
      await onRequest(`/auth/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      await onLoad();
    } catch (error) {
      showError(error);
    }
  };
  const remove = async (id: string) => {
    try {
      await onRequest(`/auth/users/${id}`, { method: "DELETE" });
      await onLoad();
    } catch (error) {
      showError(error);
    }
  };
  return (
    <>
      <PageTitle
        eyebrow="ACCESS CONTROL"
        title="Users & roles"
        description="Only administrators can change roles or remove tenant accounts."
      />
      <DataTable
        title="Tenant users"
        subtitle="Common login with enforced server-side permissions"
      >
        <table>
          <thead>
            <tr>
              <th>NAME</th>
              <th>EMAIL</th>
              <th>ROLE</th>
              <th>STATUS</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td>
                  <select
                    value={user.role}
                    onChange={(event) =>
                      void update(user.id, event.target.value)
                    }
                  >
                    <option value="user">User</option>
                    <option value="staff">Staff</option>
                    <option value="manager">Manager</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
                <td>{user.active ? "Active" : "Disabled"}</td>
                <td>
                  <button
                    className="text-button"
                    onClick={() => void remove(user.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </DataTable>
    </>
  );
}

function AssistantPanel({
  organizationId,
  userName,
  accessToken,
  onClose,
  onNavigate,
  onRefresh,
}: {
  organizationId: string;
  userName: string;
  accessToken: string;
  onClose: () => void;
  onNavigate: (target: (typeof navigation)[number][0]) => void;
  onRefresh: () => Promise<void>;
}) {
  const [tab, setTab] = useState<"chat" | "knowledge">("chat");
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      role: "assistant",
      content: `Hi ${userName.split(" ")[0]} — I’m your operations copilot. Ask me anything, or say ‘open inventory’, ‘show orders’, ‘open receiving’, or ‘refresh dashboard’.`,
    },
  ]);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");

  const headers = useCallback(
    (json = false) => {
      const result: Record<string, string> = {
        "X-Organization-Id": organizationId,
        Authorization: `Bearer ${accessToken}`,
      };
      if (json) result["Content-Type"] = "application/json";
      return result;
    },
    [organizationId, accessToken],
  );

  const loadDocuments = useCallback(async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/knowledge/documents`, {
        headers: headers(),
      });
      if (!response.ok) throw new Error("Could not load the knowledge base");
      setDocuments(await response.json());
    } catch (reason) {
      setError(readableError(reason));
    }
  }, [headers]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const speak = (text: string) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(
      text.replace(/\[[^\]]+\]/g, ""),
    );
    utterance.rate = 1.02;
    utterance.pitch = 0.95;
    window.speechSynthesis.speak(utterance);
  };

  const ask = async (question: string) => {
    const cleaned = question.trim();
    if (!cleaned || busy) return;
    const nextUser: AssistantMessage = { role: "user", content: cleaned };
    const history = messages
      .slice(-10)
      .map(({ role, content }) => ({ role, content }));
    setMessages((current) => [...current, nextUser]);
    setDraft("");
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${apiBaseUrl}/assistant/chat`, {
        method: "POST",
        headers: headers(true),
        body: JSON.stringify({ message: cleaned, history }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok)
        throw new Error(
          typeof body?.detail === "string"
            ? body.detail
            : "Assistant request failed",
        );
      const answer: AssistantMessage = {
        role: "assistant",
        content: body.answer,
        sources: body.sources,
        mode: body.mode,
      };
      setMessages((current) => [...current, answer]);
      speak(body.answer);
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setBusy(false);
    }
  };

  const respondToCommand = (question: string, response: string) => {
    setMessages((current) => [
      ...current,
      { role: "user", content: question },
      { role: "assistant", content: response, mode: "voice-command" },
    ]);
    setDraft("");
    speak(response);
  };

  const executeCommand = async (transcript: string): Promise<boolean> => {
    const command = transcript
      .toLowerCase()
      .replace(/[^a-z0-9 ]/g, "")
      .trim();
    if (
      /^(open|show|go to|take me to) (the )?(dashboard|overview)$/.test(command)
    ) {
      onNavigate("Overview");
      respondToCommand(transcript, "Opening the operations overview.");
    } else if (/^(open|show|go to|take me to) (the )?orders?$/.test(command)) {
      onNavigate("Orders");
      respondToCommand(transcript, "Opening fulfillment orders.");
    } else if (/^(create|make|start) (a |an )?(new )?order$/.test(command)) {
      onNavigate("Orders");
      respondToCommand(transcript, "Opening the order creation workflow.");
    } else if (
      /^(open|show|go to|take me to) (the )?receiving$/.test(command)
    ) {
      onNavigate("Receiving");
      respondToCommand(transcript, "Opening inbound receiving.");
    } else if (
      /^(open|show|go to|take me to) (the )?inventory$/.test(command)
    ) {
      onNavigate("Inventory");
      respondToCommand(transcript, "Opening live inventory.");
    } else if (
      /^(open|show|go to|take me to) (the )?(setup|settings)$/.test(command)
    ) {
      onNavigate("Setup");
      respondToCommand(transcript, "Opening warehouse setup.");
    } else if (
      /^(open|show) (the )?(knowledge|documents|knowledge base)$/.test(
        command,
      ) ||
      command === "upload document"
    ) {
      setTab("knowledge");
      respondToCommand(transcript, "Opening the tenant knowledge base.");
      return true;
    } else if (/^(refresh|reload)( the)?( dashboard| data)?$/.test(command)) {
      respondToCommand(transcript, "Refreshing live warehouse data.");
      await onRefresh();
      return true;
    } else if (
      /^(close|hide)( the)?( assistant| copilot| chat)?$/.test(command)
    ) {
      speak("Closing the copilot.");
      onClose();
      return true;
    } else {
      return false;
    }
    window.setTimeout(onClose, 550);
    return true;
  };

  const handleInput = async (text: string) => {
    if (!(await executeCommand(text))) await ask(text);
  };

  const startVoice = () => {
    const speechWindow = window as unknown as {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    };
    const Recognition =
      speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!Recognition) {
      setError(
        "Voice recognition is not supported by this browser. Use Chrome or Edge.",
      );
      return;
    }
    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      const transcript = event.results[event.results.length - 1][0].transcript;
      setDraft(transcript);
      setListening(false);
      void handleInput(transcript);
    };
    recognition.onerror = () => {
      setListening(false);
      setError("Microphone input failed or permission was denied.");
    };
    recognition.onend = () => setListening(false);
    setListening(true);
    setError("");
    recognition.start();
  };

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const file = data.get("file");
    if (!(file instanceof File) || !file.size) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${apiBaseUrl}/knowledge/documents`, {
        method: "POST",
        headers: headers(),
        body: data,
      });
      const body = await response.json().catch(() => null);
      if (!response.ok)
        throw new Error(
          typeof body?.detail === "string"
            ? body.detail
            : "Document upload failed",
        );
      form.reset();
      await loadDocuments();
      setTab("chat");
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: `${body.filename} is indexed. You can ask questions about it now.`,
        },
      ]);
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setBusy(false);
    }
  };

  const removeDocument = async (documentId: string) => {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `${apiBaseUrl}/knowledge/documents/${documentId}`,
        { method: "DELETE", headers: headers() },
      );
      if (!response.ok) throw new Error("Document could not be removed");
      await loadDocuments();
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="ai-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside className="ai-panel" aria-label="Whitfield operations copilot">
        <header className="ai-header">
          <div>
            <span className="ai-orb">✦</span>
            <div>
              <strong>Whitfield Copilot</strong>
              <small>Tenant-grounded operations AI</small>
            </div>
          </div>
          <button onClick={onClose} aria-label="Close assistant">
            ×
          </button>
        </header>
        <nav className="ai-tabs">
          <button
            className={tab === "chat" ? "active" : ""}
            onClick={() => setTab("chat")}
          >
            Chat & voice
          </button>
          <button
            className={tab === "knowledge" ? "active" : ""}
            onClick={() => setTab("knowledge")}
          >
            Knowledge <b>{documents.length}</b>
          </button>
        </nav>
        {error && (
          <div className="ai-error">
            {error}
            <button onClick={() => setError("")}>×</button>
          </div>
        )}
        {tab === "chat" ? (
          <>
            <div className="ai-messages">
              {messages.map((message, index) => (
                <article
                  className={`ai-message ${message.role}`}
                  key={`${message.role}-${index}`}
                >
                  <span>{message.role === "assistant" ? "AI" : "DP"}</span>
                  <div>
                    <p>{message.content}</p>
                    {message.sources?.length ? (
                      <div className="ai-sources">
                        <small>SOURCES</small>
                        {message.sources.map((source) => (
                          <button
                            title={source.excerpt}
                            key={`${source.document_id}-${source.chunk_index}`}
                          >
                            {source.filename} · p{source.chunk_index + 1}
                          </button>
                        ))}
                      </div>
                    ) : null}
                    {message.mode && (
                      <em>
                        {message.mode === "gemini"
                          ? "Gemini grounded RAG"
                          : message.mode === "openai"
                            ? "OpenAI grounded RAG"
                            : message.mode === "voice-command"
                              ? "Dashboard command"
                              : message.mode === "conversation-local"
                                ? "Local conversation"
                                : "Local extractive RAG"}
                      </em>
                    )}
                  </div>
                </article>
              ))}
              {busy && (
                <article className="ai-message assistant">
                  <span>AI</span>
                  <div className="ai-thinking">
                    <i />
                    <i />
                    <i />
                  </div>
                </article>
              )}
            </div>
            <form
              className="ai-composer"
              onSubmit={(event) => {
                event.preventDefault();
                void handleInput(draft);
              }}
            >
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder={
                  documents.length
                    ? "Ask about receiving, SLAs, inventory rules…"
                    : "Upload a warehouse PDF to begin…"
                }
                rows={3}
              />
              <div>
                <button
                  type="button"
                  className={`ai-mic ${listening ? "listening" : ""}`}
                  onClick={startVoice}
                  disabled={busy}
                >
                  {listening ? "Listening…" : "● Voice"}
                </button>
                <button className="ai-send" disabled={busy || !draft.trim()}>
                  Send →
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="ai-knowledge">
            <div>
              <h3>Tenant knowledge base</h3>
              <p>PDF, TXT, or Markdown. Files are isolated by organization.</p>
            </div>
            <form onSubmit={upload}>
              <label>
                <input
                  name="file"
                  type="file"
                  accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
                  required
                />
                <span>Choose document</span>
              </label>
              <button disabled={busy}>
                {busy ? "Indexing…" : "Upload & index"}
              </button>
            </form>
            <div className="ai-document-list">
              {documents.map((document) => (
                <article key={document.id}>
                  <span>PDF</span>
                  <div>
                    <strong>{document.filename}</strong>
                    <small>
                      {document.chunk_count} chunks ·{" "}
                      {(document.character_count / 1000).toFixed(1)}k characters
                    </small>
                  </div>
                  <button
                    onClick={() => void removeDocument(document.id)}
                    disabled={busy}
                    aria-label={`Remove ${document.filename}`}
                  >
                    ×
                  </button>
                </article>
              ))}
              {!documents.length && (
                <p>No documents indexed for this organization.</p>
              )}
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}

function PageTitle({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="subhead">{description}</p>
      </div>
    </div>
  );
}
function FormCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <article className="panel form-card">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>
      {children}
    </article>
  );
}
function DataTable({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <article className="panel data-panel">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>
      <div className="table-wrap">{children}</div>
    </article>
  );
}
function Input({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...props} />
    </label>
  );
}
function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[][];
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, optionLabel]) => (
          <option value={optionValue} key={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </label>
  );
}

function MachineId({
  value,
  compact = false,
}: {
  value: string;
  compact?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };
  return (
    <span className={`machine-id${compact ? " compact" : ""}`}>
      {!compact && <b>AUTO UUID</b>}
      <code title={value}>{value}</code>
      <button type="button" onClick={() => void copy()} aria-label="Copy UUID">
        {copied ? "Copied" : "Copy"}
      </button>
    </span>
  );
}
