import React from 'react';
import { RatingProps } from '../types';

export const Rating: React.FC<RatingProps> = ({ value, onChange, disabled = false, className = '' }) => {
    const stars = [1, 2, 3, 4, 5];

    return (
        <div className={`flex items-center space-x-1 ${className}`}>
            {stars.map((star) => (
                <button
                    key={star}
                    onClick={() => !disabled && onChange(star)}
                    disabled={disabled}
                    className={`text-2xl transition-colors ${
                        disabled
                            ? 'text-gray-300 cursor-not-allowed'
                            : 'text-gray-400 hover:text-yellow-500 cursor-pointer'
                    } ${star <= value ? 'text-yellow-500' : ''}`}
                >
                    ★
                </button>
            ))}
        </div>
    );
};

export default Rating;
