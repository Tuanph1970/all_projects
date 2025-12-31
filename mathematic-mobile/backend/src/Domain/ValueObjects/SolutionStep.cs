using Domain.Common;

namespace Domain.ValueObjects;

public class SolutionStep : ValueObject
{
    public int StepNumber { get; private set; }
    public string Description { get; private set; }
    public string? Formula { get; private set; }
    public string Explanation { get; private set; }
    public string? ImageUrl { get; private set; }
    
    public SolutionStep(int stepNumber, string description, string explanation, string? formula = null, string? imageUrl = null)
    {
        StepNumber = stepNumber;
        Description = description ?? throw new ArgumentNullException(nameof(description));
        Explanation = explanation ?? throw new ArgumentNullException(nameof(explanation));
        Formula = formula;
        ImageUrl = imageUrl;
        
        if (stepNumber <= 0)
            throw new ArgumentException("Step number must be positive", nameof(stepNumber));
    }
    
    protected override IEnumerable<object> GetEqualityComponents()
    {
        yield return StepNumber;
        yield return Description;
        yield return Formula ?? string.Empty;
        yield return Explanation;
        yield return ImageUrl ?? string.Empty;
    }
}