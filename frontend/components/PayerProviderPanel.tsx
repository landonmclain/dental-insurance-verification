"use client";

import { useMemo } from "react";

export type Contact = {
  name?: string;
  phoneNumbers?: string[];
  urls?: string[];
};

export type PayerInfo = {
  name?: string;
  id?: string;
  tin?: string;
  contacts?: Contact[];
};

export type ProviderInfo = {
  name?: string;
  npi?: string;
  type?: string;
};

export type SubscriberInfo = {
  name?: string;
  memberId?: string;
  dateOfBirth?: string;
  gender?: string;
  address?: { line1?: string; city?: string; state?: string; postalCode?: string };
  planStart?: string;
  planEnd?: string;
  groupNumber?: string;
  groupName?: string;
  planNetworkNumber?: string;
  planNetworkName?: string;
};

export function parsePayerProvider(raw: string): {
  payer: PayerInfo;
  provider: ProviderInfo;
  subscriber: SubscriberInfo;
} {
  try {
    const body = JSON.parse(raw);
    const p = body.payer ?? {};
    const prov = body.provider ?? {};
    const s = body.subscriber ?? {};

    const contacts: Contact[] = [];
    // Contacts sit on the payer object or on PAYER relatedEntities.
    for (const c of p.contacts ?? []) {
      contacts.push({
        name: c.name,
        phoneNumbers: c.phoneNumbers,
        urls: c.urls,
      });
    }
    for (const plan of body.plans ?? []) {
      for (const st of plan.benefits?.statuses ?? []) {
        for (const re of st.relatedEntities ?? []) {
          if (re.type === "PAYER") {
            for (const c of re.contacts ?? []) {
              contacts.push({
                name: c.name,
                phoneNumbers: c.phoneNumbers,
                urls: c.urls,
              });
            }
          }
        }
      }
    }

    const person = s.name?.person ?? {};
    const addr = s.address ?? {};
    const group = s.additionalInformation?.group ?? {};
    const planNetwork = s.additionalInformation?.planNetwork ?? {};
    const planDates = s.dates?.plan ?? {};

    return {
      payer: {
        name: p.name?.organization,
        id: p.identification,
        tin: p.tin,
        contacts: contacts.length ? contacts : undefined,
      },
      provider: {
        name: prov.name?.organization,
        npi: prov.npi,
        type: prov.type,
      },
      subscriber: {
        name: [person.firstName, person.lastName].filter(Boolean).join(" "),
        memberId: s.memberId,
        dateOfBirth: s.dateOfBirth,
        gender: s.gender,
        address: {
          line1: addr.addressLine1,
          city: addr.city,
          state: addr.state,
          postalCode: addr.postalCode,
        },
        planStart: planDates.start,
        planEnd: planDates.end,
        groupNumber: group.number,
        groupName: group.name,
        planNetworkNumber: planNetwork.number,
        planNetworkName: planNetwork.name,
      },
    };
  } catch {
    return { payer: {}, provider: {}, subscriber: {} };
  }
}

export function PayerProviderPanel({ raw }: { raw: string }) {
  const { payer, provider, subscriber } = useMemo(
    () => parsePayerProvider(raw),
    [raw]
  );

  return (
    <div className="mt-8 rounded-xl border bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <h2 className="mb-3 text-lg font-semibold">Payer, provider &amp; subscriber</h2>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-neutral-500">
            Payer
          </h3>
          <p className="text-sm font-medium text-slate-900 dark:text-neutral-100">{payer.name}</p>
          <div className="mt-0.5 space-y-0.5 text-xs text-slate-500 dark:text-neutral-400">
            {payer.id && <p>ID: {payer.id}</p>}
            {payer.tin && <p>TIN: {payer.tin}</p>}
          </div>
          {payer.contacts?.length ? (
            <ul className="mt-2 space-y-2 text-xs text-slate-500">
              {payer.contacts.map((c, i) => (
                <li key={i}>
                  {c.name && <div className="font-medium text-slate-600 dark:text-neutral-300">{c.name}</div>}
                  {c.phoneNumbers?.map((ph, j) => <div key={j}>{ph}</div>)}
                  {c.urls?.map((u, j) => <div key={j}>{u}</div>)}
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-neutral-500">
            Provider
          </h3>
          <p className="text-sm font-medium text-slate-900 dark:text-neutral-100">{provider.name}</p>
          <div className="mt-0.5 space-y-0.5 text-xs text-slate-500 dark:text-neutral-400">
            {provider.npi && <p>NPI: {provider.npi}</p>}
            {provider.type && <p>Type: {provider.type}</p>}
          </div>
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-neutral-500">
            Subscriber
          </h3>
          <p className="text-sm font-medium text-slate-900 dark:text-neutral-100">{subscriber.name}</p>
          <div className="mt-0.5 space-y-0.5 text-xs text-slate-500 dark:text-neutral-400">
            {subscriber.memberId && <p>Member ID: {subscriber.memberId}</p>}
            {subscriber.dateOfBirth && <p>DOB: {subscriber.dateOfBirth}</p>}
            {subscriber.gender && <p>Gender: {subscriber.gender}</p>}
            {subscriber.address?.line1 && (
              <p>
                {subscriber.address.line1}, {subscriber.address.city},{" "}
                {subscriber.address.state} {subscriber.address.postalCode}
              </p>
            )}
            {subscriber.planStart && (
              <p>
                Plan: {subscriber.planStart}
                {subscriber.planEnd ? ` – ${subscriber.planEnd}` : ""}
              </p>
            )}
            {subscriber.groupName && (
              <p>
                Group: {subscriber.groupName}
                {subscriber.groupNumber ? ` (${subscriber.groupNumber})` : ""}
              </p>
            )}
            {subscriber.planNetworkName && (
              <p>
                Network: {subscriber.planNetworkName}
                {subscriber.planNetworkNumber ? ` (${subscriber.planNetworkNumber})` : ""}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
