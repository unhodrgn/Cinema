const steps = ["Seats", "Booking", "Payment"] as const;

export function BookingSteps({ current }: { current: (typeof steps)[number] }) {
  return (
    <ol className="steps" aria-label="Booking steps">
      {steps.map((step) => (
        <li
          key={step}
          className={step === current ? "step step-current" : "step"}
          aria-current={step === current ? "step" : undefined}
        >
          {step}
        </li>
      ))}
    </ol>
  );
}
