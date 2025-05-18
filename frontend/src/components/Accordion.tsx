import React, { useState } from 'react';

interface AccordionItemProps {
  id?: string;
  title: string;
  children: React.ReactNode;
  isOpen?: boolean;
  onToggle?: () => void;
}

export const AccordionItem: React.FC<AccordionItemProps> = ({
  title,
  children,
  isOpen = false,
  onToggle,
}) => {
  return (
    <div className="border-b border-gray-200">
      <button
        className="w-full flex justify-between items-center py-4 px-4 text-left focus:outline-none"
        onClick={onToggle}
      >
        <span className="text-lg font-medium text-gray-900">{title}</span>
        <svg
          className={`w-6 h-6 transform transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {isOpen && (
        <div className="px-4 pb-4 text-gray-600">{children}</div>
      )}
    </div>
  );
};

interface AccordionProps {
  children: React.ReactElement<AccordionItemProps>[];
  allowMultiple?: boolean;
}

export const Accordion: React.FC<AccordionProps> = ({
  children,
  allowMultiple = false,
}) => {
  const [openItems, setOpenItems] = useState<string[]>([]);

  const handleToggle = (itemId: string) => {
    setOpenItems((prev) => {
      if (allowMultiple) {
        return prev.includes(itemId)
          ? prev.filter((id) => id !== itemId)
          : [...prev, itemId];
      }
      return prev.includes(itemId) ? [] : [itemId];
    });
  };

  return (
    <div className="divide-y divide-gray-200">
      {React.Children.map(children, (child) => {
        if (React.isValidElement<AccordionItemProps>(child)) {
          const itemId = child.props.id || Math.random().toString();
          return React.cloneElement(child, {
            id: itemId,
            isOpen: openItems.includes(itemId),
            onToggle: () => handleToggle(itemId),
          });
        }
        return child;
      })}
    </div>
  );
};
