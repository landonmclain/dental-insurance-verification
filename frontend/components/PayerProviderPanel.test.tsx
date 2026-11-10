import { describe, expect, it } from "vitest";
import { parsePayerProvider } from "./PayerProviderPanel";

const SAMPLE = JSON.stringify({
  payer: {
    name: { organization: "CHLIC" },
    type: "PAYER",
    contacts: [
      {
        name: "CUSTOMER SERVICE",
        phoneNumbers: ["8002446224"],
        urls: ["cignaforhcp.cigna.com"],
      },
    ],
    tin: "591031071",
  },
  provider: { name: { organization: "ONE" }, type: "PROVIDER", npi: "1999999984" },
  subscriber: {
    address: { addressLine1: "444 SPOTTED PATH", city: "RAINFOREST CITY", state: "CA", postalCode: "11111" },
    dates: { plan: { start: "2024-01-01", end: "2024-12-31" } },
    dateOfBirth: "1996-05-05",
    gender: "MALE",
    name: { person: { firstName: "JAGUAR", lastName: "DENT" } },
    additionalInformation: {
      group: { number: "7778889", name: "DENTAL GROUP" },
      planNetwork: { number: "DENTL", name: "TOTAL CIGNA DPPO" },
    },
    memberId: "U3141592653",
  },
  plans: [
    {
      benefits: {
        statuses: [
          {
            relatedEntities: [
              {
                name: { organization: "UNITEDHEALTHCARE SPECIALTY BENEFITS DENTAL" },
                type: "PAYER",
                contacts: [{ urls: ["WWW.OPTUMHEALTHDENTAL.COM"] }],
                payerId: "412014834",
              },
            ],
          },
        ],
      },
    },
  ],
});

describe("parsePayerProvider", () => {
  it("extracts payer name, id, tin, and direct contacts", () => {
    const { payer } = parsePayerProvider(SAMPLE);
    expect(payer.name).toBe("CHLIC");
    expect(payer.tin).toBe("591031071");
    expect(payer.contacts?.[0]).toEqual({
      name: "CUSTOMER SERVICE",
      phoneNumbers: ["8002446224"],
      urls: ["cignaforhcp.cigna.com"],
    });
  });

  it("merges contacts from relatedEntities", () => {
    const { payer } = parsePayerProvider(SAMPLE);
    const urls = (payer.contacts ?? []).flatMap((c) => c.urls ?? []);
    expect(urls).toContain("WWW.OPTUMHEALTHDENTAL.COM");
  });

  it("extracts provider name, npi, and type", () => {
    const { provider } = parsePayerProvider(SAMPLE);
    expect(provider).toEqual({
      name: "ONE",
      npi: "1999999984",
      type: "PROVIDER",
    });
  });

  it("extracts subscriber details", () => {
    const { subscriber } = parsePayerProvider(SAMPLE);
    expect(subscriber.name).toBe("JAGUAR DENT");
    expect(subscriber.memberId).toBe("U3141592653");
    expect(subscriber.dateOfBirth).toBe("1996-05-05");
    expect(subscriber.gender).toBe("MALE");
    expect(subscriber.address).toEqual({
      line1: "444 SPOTTED PATH",
      city: "RAINFOREST CITY",
      state: "CA",
      postalCode: "11111",
    });
    expect(subscriber.planStart).toBe("2024-01-01");
    expect(subscriber.planEnd).toBe("2024-12-31");
    expect(subscriber.groupName).toBe("DENTAL GROUP");
    expect(subscriber.groupNumber).toBe("7778889");
    expect(subscriber.planNetworkName).toBe("TOTAL CIGNA DPPO");
    expect(subscriber.planNetworkNumber).toBe("DENTL");
  });

  it("returns empty objects for invalid JSON", () => {
    expect(parsePayerProvider("nope")).toEqual({
      payer: {},
      provider: {},
      subscriber: {},
    });
  });
});
