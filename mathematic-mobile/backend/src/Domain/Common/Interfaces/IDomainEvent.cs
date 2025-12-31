using MediatR;

namespace Domain.Common.Interfaces;

public interface IDomainEvent : INotification
{
    DateTime OccurredOn { get; }
}